#!/bin/bash
# Start script for FastAPI with proper dependency installation

echo "Starting FastAPI setup..."

# Install minimal dependencies if not present
if ! python -c "import fastapi" 2>/dev/null; then
    echo "Installing FastAPI dependencies..."
    pip install fastapi==0.109.0 uvicorn==0.27.0 python-dotenv==1.0.0
else
    echo "FastAPI already installed"
fi

# Start the FastAPI app
echo "Starting FastAPI application..."
python main_simple.py