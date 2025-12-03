#!/bin/bash
# Quick deployment script with project ID pre-configured

set -e

# Configuration - Project ID is set
export GCP_PROJECT_ID="refactord-479213"
export GCP_REGION="asia-south1"
export SERVICE_NAME="cloud-refactor-agent"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}Cloud Refactor Agent Deployment${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "Project ID: ${GREEN}${GCP_PROJECT_ID}${NC}"
echo -e "Region: ${GREEN}${GCP_REGION}${NC}"
echo -e "Service: ${GREEN}${SERVICE_NAME}${NC}"
echo ""

# Default API key (can be overridden with environment variable)
# Note: Set GEMINI_API_KEY environment variable before running this script
GEMINI_API_KEY="${GEMINI_API_KEY:-}"

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    echo "Install from: https://cloud.google.com/sdk/docs/install"
    exit 1
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    echo "Install from: https://docs.docker.com/get-docker/"
    exit 1
fi

# Set the project
echo -e "${YELLOW}[1/7] Setting GCP project...${NC}"
gcloud config set project ${GCP_PROJECT_ID}

# Check if frontend is built
echo -e "${YELLOW}[1.5/7] Checking frontend build...${NC}"
if [ ! -d "frontend/build" ]; then
    echo -e "${YELLOW}Frontend build not found. Building frontend...${NC}"
    if ! command -v npm &> /dev/null; then
        echo -e "${RED}Error: npm is not installed. Please install Node.js and npm${NC}"
        exit 1
    fi
    cd frontend
    npm install
    npm run build
    cd ..
    echo -e "${GREEN}✅ Frontend built successfully${NC}"
else
    echo -e "${GREEN}✅ Frontend build found${NC}"
fi

# Enable required APIs
echo -e "${YELLOW}[2/7] Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com --quiet || true
gcloud services enable run.googleapis.com --quiet || true
gcloud services enable containerregistry.googleapis.com --quiet || true
gcloud services enable secretmanager.googleapis.com --quiet || true

# Build the Docker image
echo -e "${YELLOW}[3/7] Building Docker image...${NC}"
IMAGE_NAME="gcr.io/${GCP_PROJECT_ID}/${SERVICE_NAME}"
docker build -f Dockerfile.cloudrun -t ${IMAGE_NAME}:latest .

# Push the image to Container Registry
echo -e "${YELLOW}[4/7] Pushing image to Container Registry...${NC}"
docker push ${IMAGE_NAME}:latest

# Prepare environment variables
ENV_VARS="REQUIRE_AUTH=true,ALLOWED_EMAIL_DOMAINS=@searce.com,GCP_PROJECT_ID=${GCP_PROJECT_ID},GCP_REGION=${GCP_REGION},PYTHONUNBUFFERED=1,LOG_LEVEL=INFO,TEST_RUNNER=pytest"
if [ ! -z "$GEMINI_API_KEY" ]; then
    ENV_VARS="${ENV_VARS},GEMINI_API_KEY=${GEMINI_API_KEY}"
else
    echo -e "${YELLOW}⚠️  Warning: GEMINI_API_KEY not set. LLM features will use mock provider.${NC}"
fi

# Deploy to Cloud Run
echo -e "${YELLOW}[5/7] Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --platform managed \
    --region ${GCP_REGION} \
    --no-allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 1 \
    --set-env-vars "${ENV_VARS}" \
    --service-account cloud-refactor-agent@${GCP_PROJECT_ID}.iam.gserviceaccount.com \
    --execution-environment gen2 \
    --cpu-boost || {
    echo -e "${YELLOW}Service account doesn't exist, creating it...${NC}"
    gcloud iam service-accounts create cloud-refactor-agent \
        --display-name="Cloud Refactor Agent Service Account" \
        --project=${GCP_PROJECT_ID} || true
    
    # Retry deployment
    gcloud run deploy ${SERVICE_NAME} \
        --image ${IMAGE_NAME}:latest \
        --platform managed \
        --region ${GCP_REGION} \
        --no-allow-unauthenticated \
        --memory 2Gi \
        --cpu 2 \
        --timeout 300 \
        --max-instances 10 \
        --min-instances 1 \
        --set-env-vars "${ENV_VARS}" \
        --service-account cloud-refactor-agent@${GCP_PROJECT_ID}.iam.gserviceaccount.com \
        --execution-environment gen2
}

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${GCP_REGION} --format 'value(status.url)')

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Deployment Complete!${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo -e "Service URL: ${BLUE}${SERVICE_URL}${NC}"
echo ""

# Configure IAM for Searce users
echo -e "${YELLOW}[6/7] Configuring IAM for Searce users...${NC}"
gcloud run services add-iam-policy-binding ${SERVICE_NAME} \
    --region ${GCP_REGION} \
    --member "domain:searce.com" \
    --role "roles/run.invoker" || {
    echo -e "${YELLOW}Note: IAM policy may already be configured${NC}"
}

echo ""
echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}Next Steps:${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "1. ✅ Service deployed: ${SERVICE_URL}"
echo "2. ✅ Searce domain access configured"
echo ""
echo "3. Test the deployment:"
echo "   - Visit: ${SERVICE_URL}"
echo "   - Sign in with your @searce.com account"
echo ""
echo "4. View logs:"
echo "   gcloud run services logs read ${SERVICE_NAME} --region ${GCP_REGION}"
echo ""
echo "5. Update environment variables:"
echo "   gcloud run services update ${SERVICE_NAME} --region ${GCP_REGION} --update-env-vars KEY=VALUE"
echo ""
