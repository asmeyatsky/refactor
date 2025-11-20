# API Server Status ✅

## Server is Running!

**Status**: ✅ **ACTIVE**
**URL**: http://localhost:8000
**Health Check**: http://localhost:8000/api/health

## Quick Test

```bash
# Health check
curl http://localhost:8000/api/health

# Get supported services
curl http://localhost:8000/api/services
```

## How to Start/Stop

### Start the API Server

**Option 1: Using the start script**
```bash
./start_api.sh
```

**Option 2: Using venv Python directly**
```bash
venv/bin/python api_server.py
```

**Option 3: Manual activation**
```bash
source venv/bin/activate
python api_server.py
```

### Stop the API Server

Press `Ctrl+C` in the terminal, or:
```bash
lsof -ti:8000 | xargs kill -9
```

## Frontend Connection

The frontend at http://localhost:3001 is configured to connect to:
- **API Base URL**: http://localhost:8000

Make sure both servers are running:
- ✅ Frontend: http://localhost:3001
- ✅ Backend API: http://localhost:8000

## Troubleshooting

### Port Already in Use
```bash
# Check what's using port 8000
lsof -ti:8000

# Kill the process
lsof -ti:8000 | xargs kill -9
```

### Module Not Found Errors
Make sure you're using the virtual environment:
```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Connection Refused
1. Check if server is running: `curl http://localhost:8000/api/health`
2. Check firewall settings
3. Verify the port in `.env` matches

## API Endpoints

- `GET /api/health` - Health check
- `GET /api/services` - Get supported services
- `POST /api/migrate` - Initiate migration
- `GET /api/migration/{id}` - Get migration status

## Next Steps

Now that the API is running, you can:
1. ✅ Use the frontend at http://localhost:3001
2. ✅ Test migrations through the web UI
3. ✅ Use the API directly via curl or Postman

Happy migrating! 🚀
