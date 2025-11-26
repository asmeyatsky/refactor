#!/bin/bash
# Deployment script for Cloud Run

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

echo -e "${GREEN}Deploying Cloud Refactor Agent to Cloud Run${NC}"
echo "Project: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Service: ${SERVICE_NAME}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo -e "${RED}Error: gcloud CLI is not installed${NC}"
    exit 1
fi

# Check if docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed${NC}"
    exit 1
fi

# Configure Docker to use gcloud as a credential helper for GCR
echo -e "${YELLOW}Configuring Docker authentication for GCR...${NC}"
gcloud auth configure-docker --quiet

# Set the project
echo -e "${YELLOW}Setting GCP project...${NC}"
gcloud config set project ${PROJECT_ID}

# Enable required APIs
echo -e "${YELLOW}Enabling required APIs...${NC}"
gcloud services enable cloudbuild.googleapis.com
gcloud services enable run.googleapis.com
gcloud services enable containerregistry.googleapis.com

# Check if service account exists, create if not
SERVICE_ACCOUNT_EMAIL="cloud-refactor-agent@${PROJECT_ID}.iam.gserviceaccount.com"
echo -e "${YELLOW}Checking service account...${NC}"
if ! gcloud iam service-accounts describe ${SERVICE_ACCOUNT_EMAIL} &>/dev/null; then
    echo -e "${YELLOW}Creating service account...${NC}"
    gcloud iam service-accounts create cloud-refactor-agent \
        --display-name="Cloud Refactor Agent Service Account" \
        --description="Service account for Cloud Refactor Agent on Cloud Run"
else
    echo -e "${GREEN}Service account already exists${NC}"
fi

# Check for required environment variables
if [ -z "${GEMINI_API_KEY}" ]; then
    echo -e "${YELLOW}Warning: GEMINI_API_KEY not set. The service may not work without it.${NC}"
    echo -e "${YELLOW}You can set it later with:${NC}"
    echo "  gcloud run services update ${SERVICE_NAME} --region ${REGION} --update-env-vars GEMINI_API_KEY=your-key"
    ENV_VARS="REQUIRE_AUTH=true,ALLOWED_EMAIL_DOMAINS=@searce.com,GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},USE_CLOUD_RUN_IAM=true"
else
    ENV_VARS="REQUIRE_AUTH=true,ALLOWED_EMAIL_DOMAINS=@searce.com,GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},USE_CLOUD_RUN_IAM=true,GEMINI_API_KEY=${GEMINI_API_KEY}"
fi

# Build and push using Cloud Build (ensures correct architecture for Cloud Run)
echo -e "${YELLOW}Building Docker image with Cloud Build...${NC}"
gcloud builds submit --tag ${IMAGE_NAME}:latest --timeout=20m

# Deploy to Cloud Run with authentication required
echo -e "${YELLOW}Deploying to Cloud Run...${NC}"
gcloud run deploy ${SERVICE_NAME} \
    --image ${IMAGE_NAME}:latest \
    --platform managed \
    --region ${REGION} \
    --no-allow-unauthenticated \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 0 \
    --set-env-vars "${ENV_VARS}" \
    --service-account ${SERVICE_ACCOUNT_EMAIL}

# Allow Searce domain and specific users to access (SSO will be enforced)
echo -e "${YELLOW}Configuring IAM for Searce SSO...${NC}"
# Allow Searce domain
gcloud run services add-iam-policy-binding ${SERVICE_NAME} \
    --region ${REGION} \
    --member "domain:searce.com" \
    --role "roles/run.invoker" \
    --quiet || echo -e "${YELLOW}Searce domain access already configured${NC}"

# Also allow allUsers for public access (users will still need to authenticate via Google Sign-In)
echo -e "${YELLOW}Allowing public access (with authentication required)...${NC}"
gcloud run services add-iam-policy-binding ${SERVICE_NAME} \
    --region ${REGION} \
    --member "allUsers" \
    --role "roles/run.invoker" \
    --quiet || echo -e "${YELLOW}Public access already configured${NC}"

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
if [ -z "${GEMINI_API_KEY}" ]; then
    echo "2. Set GEMINI_API_KEY (required for LLM features):"
    echo "   gcloud run services update ${SERVICE_NAME} \\"
    echo "     --region ${REGION} \\"
    echo "     --update-env-vars GEMINI_API_KEY=your-api-key"
    echo ""
fi
echo "3. Access the application at: ${SERVICE_URL}"
echo ""
echo -e "${YELLOW}Note:${NC} Cloud Run IAM authentication is enabled. Users will be redirected"
echo "to Google Sign-In when accessing the service URL."
