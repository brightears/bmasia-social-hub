#!/bin/bash
# BMA Social API startup script with debugging

echo "BMA Social API starting..."
echo "Environment: ${ENVIRONMENT:-development}"
echo "Port: ${PORT:-8000}"
echo "Python version: $(python --version)"
echo "Current directory: $(pwd)"

# Check if we're in the backend directory
if [ ! -f "app/main.py" ]; then
    echo "Error: app/main.py not found. Are we in the backend directory?"
    ls -la
    exit 1
fi

# Set default values if not provided
export HOST="${HOST:-0.0.0.0}"
export PORT="${PORT:-8000}"
export WORKERS="${WORKERS:-1}"
export LOG_LEVEL="${LOG_LEVEL:-INFO}"

# Log environment variables (without secrets)
echo "Configuration:"
echo "  HOST: $HOST"
echo "  PORT: $PORT"
echo "  WORKERS: $WORKERS"
echo "  LOG_LEVEL: $LOG_LEVEL"
echo "  DATABASE_URL: ${DATABASE_URL:+[configured]}"
echo "  REDIS_URL: ${REDIS_URL:+[configured]}"

# Start the application with uvicorn
echo "Starting uvicorn server..."
exec uvicorn app.main:app \
    --host $HOST \
    --port $PORT \
    --workers $WORKERS \
    --log-level ${LOG_LEVEL,,} \
    --access-log \
    --timeout-keep-alive 75 \
    --no-use-colors