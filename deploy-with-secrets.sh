#!/bin/bash
# Deployment script for Cloud Run with Secret Manager integration

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-refactord-479213}"
REGION="${GCP_REGION:-asia-south1}"
SERVICE_NAME="cloud-refactor-agent"
IMAGE_NAME="gcr.io/${PROJECT_ID}/${SERVICE_NAME}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}Deploying Cloud Refactor Agent to Cloud Run (with Secret Manager)${NC}"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Check prerequisites
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    exit 1
fi

if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Set the project
gcloud config set project ${PROJECT_ID}

# Configure Docker authentication
gcloud auth configure-docker --quiet

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable secretmanager.googleapis.com

# Check/create service account
SERVICE_ACCOUNT_EMAIL="cloud-refactor-agent@${PROJECT_ID}.iam.gserviceaccount.com"
if ! gcloud iam service-accounts describe ${SERVICE_ACCOUNT_EMAIL} &>/dev/null; then
    echo -e "${YELLOW}Creating service account...${NC}"
    gcloud iam service-accounts create cloud-refactor-agent \
        --display-name="Cloud Refactor Agent Service Account" \
        --description="Service account for Cloud Refactor Agent on Cloud Run"
fi

# Check/create secrets
SECRET_NAME="gemini-api-key"
if ! gcloud secrets describe ${SECRET_NAME} &>/dev/null 2>&1; then
    echo -e "${YELLOW}Creating secret for GEMINI_API_KEY...${NC}"
    if [ -z "${GEMINI_API_KEY}" ]; then
        echo -e "${RED}Error: GEMINI_API_KEY environment variable is required${NC}"
        echo "Please set it: export GEMINI_API_KEY=your-api-key"
        exit 1
    fi
    echo -n "${GEMINI_API_KEY}" | gcloud secrets create ${SECRET_NAME} --data-file=-
else
    echo -e "${GREEN}Secret already exists${NC}"
    if [ -n "${GEMINI_API_KEY}" ]; then
        echo -e "${YELLOW}Updating secret...${NC}"
        echo -n "${GEMINI_API_KEY}" | gcloud secrets versions add ${SECRET_NAME} --data-file=-
    fi
fi

# Grant service account access to secret
gcloud secrets add-iam-policy-binding ${SECRET_NAME} \
    --member "serviceAccount:${SERVICE_ACCOUNT_EMAIL}" \
    --role "roles/secretmanager.secretAccessor" \
    --quiet || true

# Build and push Docker image
echo -e "${YELLOW}Building Docker image...${NC}"
docker build -f Dockerfile.cloudrun -t ${IMAGE_NAME}:latest .

echo -e "${YELLOW}Pushing image to Container Registry...${NC}"
docker push ${IMAGE_NAME}:latest

# Deploy to Cloud Run with secrets
echo -e "${YELLOW}Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated=false \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0 \
    --set-env-vars "REQUIRE_AUTH=true,ALLOWED_EMAIL_DOMAINS=@searce.com,GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},USE_CLOUD_RUN_IAM=true" \
    --update-secrets GEMINI_API_KEY=${SECRET_NAME}:latest \
    --service-account ${SERVICE_ACCOUNT_EMAIL}

# Get the service URL
SERVICE_URL=$(gcloud run services describe ${SERVICE_NAME} --region ${REGION} --format 'value(status.url)')

echo ""
echo -e "${GREEN}Deployment complete!${NC}"
echo -e "Service URL: ${SERVICE_URL}"
echo ""
echo -e "${YELLOW}Next steps:${NC}"
echo "1. Configure IAM to allow Searce users:"
echo "   gcloud run services add-iam-policy-binding ${SERVICE_NAME} \\"
echo "     --region ${REGION} \\"
echo "     --member 'domain:searce.com' \\"
echo "     --role 'roles/run.invoker'"
echo ""
echo "2. Access the application at: ${SERVICE_URL}"
echo ""
echo -e "${YELLOW}Note:${NC} Cloud Run IAM authentication is enabled. Users will be redirected"
echo "to Google Sign-In when accessing the service URL."
