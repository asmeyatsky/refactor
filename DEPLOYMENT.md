# Cloud Run Deployment Guide

This guide explains how to deploy the Cloud Refactor Agent to Google Cloud Run with Searce SSO authentication.

## Prerequisites

1. **Google Cloud Project** with billing enabled
2. **gcloud CLI** installed and configured
3. **Docker** installed
4. **Searce OAuth credentials** (if using custom OAuth)

## Architecture

The application is deployed as a single container on Cloud Run that:
- Serves the FastAPI backend
- Serves the React frontend (static files)
- Requires Searce authentication via Cloud Run IAM or OAuth

## Deployment Options

### Option 1: Quick Deploy Script (Recommended)

```bash
# Set environment variables
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="asia-south1"
export GEMINI_API_KEY="your-gemini-api-key"

# Make script executable
chmod +x cloudrun-deploy.sh

# Run deployment
./cloudrun-deploy.sh
```

### Option 2: Manual Deployment

#### Step 1: Build and Push Docker Image

```bash
# Set your project ID
export PROJECT_ID="your-project-id"
export REGION="asia-south1"

# Build the image
docker build -f Dockerfile.cloudrun -t gcr.io/${PROJECT_ID}/cloud-refactor-agent:latest .

# Push to Container Registry
docker push gcr.io/${PROJECT_ID}/cloud-refactor-agent:latest
```

#### Step 2: Deploy to Cloud Run

```bash
gcloud run deploy cloud-refactor-agent \
    --image gcr.io/${PROJECT_ID}/cloud-refactor-agent:latest \
    --platform managed \
    --region ${REGION} \
    --allow-unauthenticated=false \
    --memory 2Gi \
    --cpu 2 \
    --timeout 300 \
    --max-instances 10 \
    --min-instances 1 \
    --set-env-vars "REQUIRE_AUTH=true,ALLOWED_EMAIL_DOMAINS=@searce.com,GCP_PROJECT_ID=${PROJECT_ID},GCP_REGION=${REGION},GEMINI_API_KEY=${GEMINI_API_KEY}"
```

#### Step 3: Configure IAM for Searce Users

```bash
# Allow all Searce users to access the service
gcloud run services add-iam-policy-binding cloud-refactor-agent \
    --region ${REGION} \
    --member "domain:searce.com" \
    --role "roles/run.invoker"
```

### Option 3: Cloud Build (CI/CD)

```bash
# Submit build to Cloud Build
gcloud builds submit --config cloudbuild.yaml \
    --substitutions _REGION=${REGION},_GEMINI_API_KEY=${GEMINI_API_KEY}
```

## Authentication Configuration

### Cloud Run IAM Authentication (Recommended)

Cloud Run IAM authentication is the simplest option. Users authenticate with their Google accounts, and Cloud Run validates the identity token.

**Setup:**
1. Deploy with `--allow-unauthenticated=false`
2. Grant access to Searce domain:
   ```bash
   gcloud run services add-iam-policy-binding cloud-refactor-agent \
       --region ${REGION} \
       --member "domain:searce.com" \
       --role "roles/run.invoker"
   ```

**How it works:**
- Users access the Cloud Run URL
- Google Cloud redirects to Google Sign-In
- Users sign in with their @searce.com account
- Cloud Run validates the identity token
- Application receives authenticated request

### Custom OAuth Authentication

If you need custom OAuth (e.g., Searce SSO provider), configure environment variables:

```bash
gcloud run services update cloud-refactor-agent \
    --region ${REGION} \
    --update-env-vars "SEARCE_OAUTH_CLIENT_ID=your-client-id,SEARCE_OAUTH_CLIENT_SECRET=your-client-secret,SEARCE_OAUTH_DOMAIN=searce.com"
```

## Environment Variables

| Variable | Description | Required | Default |
|----------|-------------|----------|---------|
| `REQUIRE_AUTH` | Enable authentication | No | `false` |
| `ALLOWED_EMAIL_DOMAINS` | Allowed email domains (comma-separated) | No | `@searce.com` |
| `GEMINI_API_KEY` | Gemini API key for LLM | Yes | - |
| `GCP_PROJECT_ID` | GCP Project ID | Yes | - |
| `GCP_REGION` | GCP Region | No | `asia-south1` |
| `SEARCE_OAUTH_CLIENT_ID` | OAuth Client ID (if using custom OAuth) | No | - |
| `SEARCE_OAUTH_CLIENT_SECRET` | OAuth Client Secret (if using custom OAuth) | No | - |
| `USE_CLOUD_RUN_IAM` | Use Cloud Run IAM auth | No | `true` |

## Service Account Setup

Create a service account for the Cloud Run service:

```bash
# Create service account
gcloud iam service-accounts create cloud-refactor-agent \
    --display-name="Cloud Refactor Agent Service Account"

# Grant necessary permissions
gcloud projects add-iam-policy-binding ${PROJECT_ID} \
    --member "serviceAccount:cloud-refactor-agent@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role "roles/run.invoker"
```

## Monitoring and Logging

### View Logs

```bash
gcloud run services logs read cloud-refactor-agent --region ${REGION}
```

### Monitor Metrics

- Go to Cloud Console → Cloud Run → cloud-refactor-agent
- View metrics: requests, latency, errors, etc.

## Troubleshooting

### Service won't start

1. Check logs: `gcloud run services logs read cloud-refactor-agent --region ${REGION}`
2. Verify environment variables are set correctly
3. Check service account permissions

### Authentication not working

1. Verify IAM policy binding: `gcloud run services get-iam-policy cloud-refactor-agent --region ${REGION}`
2. Check `ALLOWED_EMAIL_DOMAINS` environment variable
3. Verify OAuth credentials (if using custom OAuth)

### Frontend not loading

1. Verify frontend build exists: `ls -la frontend/build/`
2. Check that static files are being served correctly
3. Verify CORS settings in `api_server.py`

## Cost Optimization

- **Min instances**: Set to 0 for cost savings (cold starts acceptable)
- **Max instances**: Adjust based on expected load
- **Memory/CPU**: Start with 2Gi/2 CPU, adjust based on usage
- **Timeout**: Set to 300s (5 minutes) for long-running migrations

## Security Best Practices

1. **Never commit secrets**: Use Secret Manager for sensitive values
2. **Use IAM**: Prefer Cloud Run IAM over custom OAuth when possible
3. **Restrict access**: Only allow Searce domain users
4. **Enable audit logs**: Monitor access and changes
5. **Regular updates**: Keep dependencies updated

## Using Secret Manager (Recommended)

For sensitive values like API keys:

```bash
# Create secrets
echo -n "your-gemini-api-key" | gcloud secrets create gemini-api-key --data-file=-

# Grant access to service account
gcloud secrets add-iam-policy-binding gemini-api-key \
    --member "serviceAccount:cloud-refactor-agent@${PROJECT_ID}.iam.gserviceaccount.com" \
    --role "roles/secretmanager.secretAccessor"

# Update Cloud Run to use secret
gcloud run services update cloud-refactor-agent \
    --region ${REGION} \
    --update-secrets GEMINI_API_KEY=gemini-api-key:latest
```

## Next Steps

1. Deploy the service using one of the methods above
2. Configure IAM for Searce users
3. Test authentication flow
4. Monitor logs and metrics
5. Set up alerts for errors

## Support

For issues or questions, contact the development team or check the logs.
