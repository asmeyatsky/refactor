# Quick Deployment Guide - Cloud Run with Searce Authentication

## Prerequisites

1. **gcloud CLI** installed and authenticated
2. **Docker** installed
3. **GCP Project** with billing enabled
4. **Gemini API Key** (for LLM features

## Quick Start (5 minutes)

### 1. Set Environment Variables

```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="asia-south1"
export GEMINI_API_KEY="your-gemini-api-key"
```

### 2. Run Deployment Script

```bash
chmod +x cloudrun-deploy.sh
./cloudrun-deploy.sh
```

### 3. Configure Searce Access

```bash
gcloud run services add-iam-policy-binding cloud-refactor-agent \
    --region ${GCP_REGION} \
    --member "domain:searce.com" \
    --role "roles/run.invoker"
```

## How Authentication Works

### Cloud Run IAM (Recommended - No Code Changes Needed)

1. **Deploy with `--allow-unauthenticated=false`**
2. **Grant access to Searce domain** (see step 3 above)
3. **Users access the URL** → Google Cloud redirects to sign-in
4. **Users sign in with @searce.com account** → Access granted

**Benefits:**
- No OAuth setup required
- Uses Google's built-in authentication
- Automatic token validation
- Works seamlessly with Searce Google Workspace accounts

### Custom OAuth (If Needed)

If Searce uses a custom SSO provider:

1. Set environment variables:
   ```bash
   gcloud run services update cloud-refactor-agent \
       --region ${GCP_REGION} \
       --update-env-vars "SEARCE_OAUTH_CLIENT_ID=xxx,SEARCE_OAUTH_CLIENT_SECRET=xxx"
   ```

2. Configure OAuth redirect URI in your provider

## Architecture

```
┌─────────────┐
│   Browser   │
└──────┬──────┘
       │
       │ HTTPS Request
       ▼
┌─────────────────────────────────┐
│      Cloud Run (IAM Auth)       │
│  ┌───────────────────────────┐  │
│  │  FastAPI Backend          │  │
│  │  - API Routes             │  │
│  │  - Static Frontend Files  │  │
│  │  - Authentication         │  │
│  └───────────────────────────┘  │
└─────────────────────────────────┘
```

## Key Files

- **`Dockerfile.cloudrun`**: Production Docker image
- **`cloudrun-deploy.sh`**: Automated deployment script
- **`DEPLOYMENT.md`**: Detailed deployment guide
- **`infrastructure/adapters/auth_middleware.py`**: Authentication logic

## Environment Variables

Set these in Cloud Run:

| Variable | Value | Required |
|----------|-------|----------|
| `REQUIRE_AUTH` | `true` | Yes |
| `ALLOWED_EMAIL_DOMAINS` | `@searce.com` | Yes |
| `GEMINI_API_KEY` | Your API key | Yes |
| `GCP_PROJECT_ID` | Your project ID | Yes |
| `GCP_REGION` | `asia-south1` | No |

## Troubleshooting

**Service won't start:**
```bash
gcloud run services logs read cloud-refactor-agent --region ${GCP_REGION} --limit 50
```

**Authentication not working:**
```bash
# Check IAM policy
gcloud run services get-iam-policy cloud-refactor-agent --region ${GCP_REGION}

# Verify domain access
gcloud run services add-iam-policy-binding cloud-refactor-agent \
    --region ${GCP_REGION} \
    --member "user:your.email@searce.com" \
    --role "roles/run.invoker"
```

**Frontend not loading:**
- Ensure frontend is built: `cd frontend && npm run build`
- Check that `frontend/build` directory exists in Docker image

## Cost Estimate

- **Min instances: 1** = ~$25/month (always running)
- **Min instances: 0** = Pay per request (~$0.40 per million requests)
- **Memory: 2Gi** = Included in Cloud Run pricing
- **CPU: 2** = Included in Cloud Run pricing

**Recommendation:** Start with `min-instances=1` for better UX, then reduce to 0 if cost is a concern.

## Next Steps

1. ✅ Deploy to Cloud Run
2. ✅ Configure Searce domain access
3. ✅ Test authentication flow
4. ✅ Monitor logs and metrics
5. ✅ Set up alerts

For detailed information, see `DEPLOYMENT.md`.
