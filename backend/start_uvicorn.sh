#!/bin/bash
# Direct uvicorn startup script for maximum Render compatibility
# This bypasses Python startup scripts entirely

echo "==============================================="
echo "BMA Social API - Direct uvicorn startup"
echo "==============================================="
echo "Python version: $(python --version)"
echo "Working directory: $(pwd)"
echo "PORT: ${PORT:-NOT SET}"
echo "ENVIRONMENT: ${ENVIRONMENT:-NOT SET}"
echo "==============================================="

# Use PORT environment variable or default to 8000
PORT=${PORT:-8000}

echo "Starting uvicorn directly on port $PORT..."

# Start uvicorn directly with the FastAPI app
uvicorn minimal_start:app \
  --host 0.0.0.0 \
  --port $PORT \
  --log-level info \
  --access-log \
  --no-server-header \
  --timeout-keep-alive 75