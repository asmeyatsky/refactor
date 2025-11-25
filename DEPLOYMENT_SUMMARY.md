# Cloud Run Deployment Summary

## Overview

The Cloud Refactor Agent has been containerized and configured for deployment to Google Cloud Run with Searce SSO authentication.

## Architecture

### Single Container Deployment
- **Backend**: FastAPI server (Python)
- **Frontend**: React app (served as static files)
- **Authentication**: Cloud Run IAM (Searce domain restriction)
- **Runtime**: Cloud Run (serverless, auto-scaling)

### Key Features
✅ Single container (backend + frontend)  
✅ Searce authentication via Cloud Run IAM  
✅ Auto-scaling (1-10 instances)  
✅ Health checks and monitoring  
✅ Static file serving  
✅ Progress tracking  
✅ Validation agent  

## Files Created

### Deployment Files
1. **`Dockerfile.cloudrun`** - Production Docker image
   - Multi-stage build (frontend + backend)
   - Optimized for Cloud Run
   - Uses gunicorn for production

2. **`cloudrun-deploy.sh`** - Automated deployment script
   - Builds Docker image
   - Pushes to Container Registry
   - Deploys to Cloud Run
   - Configures IAM

3. **`cloudbuild.yaml`** - Cloud Build CI/CD configuration
   - Automated builds on git push
   - Deploys to Cloud Run

4. **`cloudrun-service.yaml`** - Kubernetes/Cloud Run service definition
   - Service configuration
   - Resource limits
   - Health probes

### Authentication
5. **`infrastructure/adapters/auth_middleware.py`** - Authentication middleware
   - Cloud Run IAM validation
   - OAuth token validation
   - Domain restriction (Searce only)

### Documentation
6. **`DEPLOYMENT.md`** - Comprehensive deployment guide
7. **`QUICK_DEPLOY.md`** - Quick start guide

## Deployment Methods

### Method 1: Quick Deploy Script (Recommended)
```bash
export GCP_PROJECT_ID="your-project-id"
export GEMINI_API_KEY="your-key"
./cloudrun-deploy.sh
```

### Method 2: Manual gcloud Commands
```bash
# Build and push
docker build -f Dockerfile.cloudrun -t gcr.io/PROJECT_ID/cloud-refactor-agent:latest .
docker push gcr.io/PROJECT_ID/cloud-refactor-agent:latest

# Deploy
gcloud run deploy cloud-refactor-agent \
    --image gcr.io/PROJECT_ID/cloud-refactor-agent:latest \
    --platform managed \
    --region asia-south1 \
    --allow-unauthenticated=false \
    --memory 2Gi --cpu 2
```

### Method 3: Cloud Build (CI/CD)
```bash
gcloud builds submit --config cloudbuild.yaml
```

## Authentication Setup

### Cloud Run IAM (Recommended)
1. Deploy with `--allow-unauthenticated=false`
2. Grant Searce domain access:
   ```bash
   gcloud run services add-iam-policy-binding cloud-refactor-agent \
       --region asia-south1 \
       --member "domain:searce.com" \
       --role "roles/run.invoker"
   ```

**How it works:**
- User accesses Cloud Run URL
- Google Cloud redirects to Google Sign-In
- User signs in with @searce.com account
- Cloud Run validates identity token
- Application receives authenticated request

### Custom OAuth (If Needed)
Set environment variables:
- `SEARCE_OAUTH_CLIENT_ID`
- `SEARCE_OAUTH_CLIENT_SECRET`
- `SEARCE_OAUTH_DOMAIN`

## Environment Variables

Required:
- `REQUIRE_AUTH=true`
- `ALLOWED_EMAIL_DOMAINS=@searce.com`
- `GEMINI_API_KEY=<your-key>`
- `GCP_PROJECT_ID=<your-project>`

Optional:
- `GCP_REGION=asia-south1`
- `USE_CLOUD_RUN_IAM=true`
- `SEARCE_OAUTH_CLIENT_ID` (if using custom OAuth)
- `SEARCE_OAUTH_CLIENT_SECRET` (if using custom OAuth)

## Resource Configuration

- **Memory**: 2Gi (sufficient for LLM operations)
- **CPU**: 2 (for parallel processing)
- **Timeout**: 300s (5 minutes for long migrations)
- **Min Instances**: 1 (for better UX, reduce to 0 for cost savings)
- **Max Instances**: 10 (auto-scales based on load)

## Cost Estimate

**With min-instances=1:**
- ~$25/month base cost (always running)
- Pay per request: ~$0.40 per million requests

**With min-instances=0:**
- Pay per request only
- Cold start: ~5-10 seconds
- Better for cost optimization

## Security

✅ **Authentication Required**: Only Searce users can access  
✅ **Domain Restriction**: Validates @searce.com email domain  
✅ **IAM Integration**: Uses Google Cloud IAM for validation  
✅ **HTTPS Only**: Cloud Run enforces HTTPS  
✅ **No Public Access**: `--allow-unauthenticated=false`  

## Monitoring

- **Logs**: `gcloud run services logs read cloud-refactor-agent --region asia-south1`
- **Metrics**: Cloud Console → Cloud Run → Metrics
- **Alerts**: Set up in Cloud Monitoring

## Next Steps

1. ✅ Review deployment files
2. ✅ Set environment variables
3. ✅ Run deployment script
4. ✅ Configure Searce domain access
5. ✅ Test authentication
6. ✅ Monitor and optimize

## Support

For detailed instructions, see:
- `DEPLOYMENT.md` - Full deployment guide
- `QUICK_DEPLOY.md` - Quick start guide
