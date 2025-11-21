# Starting Backend and Frontend Services

## Quick Start

Both services are now running:

### Backend API Server
- **Status:** ✅ Running
- **URL:** http://localhost:8000
- **Health Check:** http://localhost:8000/api/health
- **API Docs:** http://localhost:8000/docs (Swagger UI)

### Frontend React App
- **Status:** ✅ Starting
- **URL:** http://localhost:3000 (default React port)
- **API Connection:** Configured to connect to http://localhost:8000

## Service Details

### Backend (FastAPI)
- **Port:** 8000
- **Process:** Running in background
- **Logs:** Check terminal output or logs

### Frontend (React)
- **Port:** 3000 (default)
- **Process:** Running in background
- **Hot Reload:** Enabled (auto-refreshes on code changes)

## Access Points

1. **Frontend UI:** http://localhost:3000
2. **Backend API:** http://localhost:8000
3. **API Documentation:** http://localhost:8000/docs
4. **Health Check:** http://localhost:8000/api/health

## Stopping Services

To stop the services:
```bash
# Find and kill backend process
lsof -ti:8000 | xargs kill

# Find and kill frontend process
lsof -ti:3000 | xargs kill
```

Or use Ctrl+C in the respective terminal windows.

## Troubleshooting

### Backend not starting?
- Check if port 8000 is already in use: `lsof -i:8000`
- Verify Python dependencies: `pip install -r requirements.txt`
- Check for errors in terminal output

### Frontend not starting?
- Check if port 3000 is already in use: `lsof -i:3000`
- Verify Node dependencies: `cd frontend && npm install`
- Check for errors in terminal output

### CORS Issues?
- Backend CORS is configured for:
  - http://localhost:3000
  - http://localhost:3001
  - http://127.0.0.1:3000
  - http://127.0.0.1:3001

## Next Steps

1. Open http://localhost:3000 in your browser
2. Select a cloud provider (AWS or Azure)
3. Choose input method (Code Snippet or Repository)
4. Start migrating!
