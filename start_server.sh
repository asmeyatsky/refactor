#!/bin/bash
# Startup script for Cloud Run
# Ensures server is ready before Cloud Run health check

set -e

PORT=${PORT:-8080}

# Start uvicorn in background
uvicorn api_server:app \
    --host 0.0.0.0 \
    --port ${PORT} \
    --timeout-keep-alive 5 \
    --log-level warning &

UVICORN_PID=$!

# Wait for server to be ready
echo "Waiting for server to start..."
for i in {1..30}; do
    if curl -f http://localhost:${PORT}/api/health > /dev/null 2>&1; then
        echo "Server is ready!"
        wait $UVICORN_PID
        exit 0
    fi
    sleep 1
done

echo "Server failed to start in time"
kill $UVICORN_PID
exit 1
