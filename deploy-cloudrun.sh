#!/bin/bash
# Deploy Cloud Refactor Agent to Google Cloud Run
# This script builds and deploys the service with all latest improvements

set -e  # Exit on error

# Configuration
PROJECT_ID="refactord-479213"
REGION="asia-south1"
SERVICE_NAME="cloud-refactor-agent"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"
SERVICE_ACCOUNT="${SERVICE_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "🚀 Deploying Cloud Refactor Agent to Cloud Run"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "❌ Error: gcloud CLI is not installed"
    echo "Please install it from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if user is authenticated
if ! gcloud auth list --filter=status:ACTIVE --format="value(account)" | grep -q .; then
    echo "⚠️  Not authenticated with gcloud. Please run: gcloud auth login"
    exit 1
fi

# Set the project
echo "📋 Setting GCP project..."
gcloud config set project ${PROJECT_ID}

# Check if frontend is built
if [ ! -d "frontend/build" ]; then
    echo "⚠️  Frontend build not found. Building frontend..."
    cd frontend
    if ! command -v npm &> /dev/null; then
        echo "❌ Error: npm is not installed. Please install Node.js and npm"
        exit 1
    fi
    npm install
    npm run build
    cd ..
    echo "✅ Frontend built successfully"
fi

# Build the Docker image
echo "🔨 Building Docker image..."
docker build -f Dockerfile.cloudrun -t ${IMAGE_NAME}:latest .

# Tag with commit SHA for versioning
COMMIT_SHA=$(git rev-parse --short=$(git rev-parse --short HEAD)
docker tag ${IMAGE_NAME}:latest ${IMAGE_NAME}:${COMMIT_SHA}

# Push to Google Container Registry
echo "📤 Pushing image to GCR..."
docker push ${IMAGE_NAME}:latest
docker push ${IMAGE_NAME}:${COMMIT_SHA}

# Deploy to Cloud Run
echo "🚀 Deploying to Cloud Run..."
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:${COMMIT_SHA} \
    --platform managed \
    --region ${REGION} \
    --service-account ${SERVICE_ACCOUNT} \
    --allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 1 \
    --set-env-vars "PORT=8080,PYTHONUNBUFFERED=1,LOG_LEVEL=INFO,TEST_RUNNER=pytest,GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION}" \
    --update-env-vars "REQUIRE_AUTH=true,USE_CLOUD_RUN_IAM=true,ALLOWED_EMAIL_DOMAINS=@searce.com" \
    --execution-environment gen2 \
    --cpu-throttling \
    --concurrency 80

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

echo ""
echo "✅ Deployment completed successfully!"
echo "🌐 Service URL: ${SERVICE_URL}"
echo "📊 View logs: gcloud run services logs read ${SERVICE_NAME} --region ${REGION}"
echo ""
echo "🧪 Testing health endpoint..."
curl -f ${SERVICE_URL}/api/health && echo " ✅ Health check passed!" || echo " ⚠️  Health check failed"
