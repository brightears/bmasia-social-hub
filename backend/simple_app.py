#!/usr/bin/env python3
"""
Ultra-minimal FastAPI app for Render deployment
This is the simplest possible app that will pass health checks
"""

import os
import sys
import logging
from datetime import datetime

# Configure logging to stdout for Render visibility
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler(sys.stdout)]
)

logger = logging.getLogger(__name__)

# Log startup immediately
logger.info("=== SIMPLE APP STARTUP INITIATED ===")
logger.info(f"Python version: {sys.version}")
logger.info(f"Current working directory: {os.getcwd()}")

try:
    from fastapi import FastAPI
    from fastapi.responses import JSONResponse
    import uvicorn
    
    logger.info("FastAPI and uvicorn imported successfully")
    
except ImportError as e:
    logger.error(f"Failed to import required packages: {e}")
    sys.exit(1)

# Create FastAPI app
app = FastAPI(
    title="BMA Social Hub - Simple",
    description="Ultra-minimal FastAPI app for health checks",
    version="1.0.0"
)

logger.info("FastAPI app created successfully")

@app.get("/")
async def root():
    """Root endpoint"""
    return {"message": "BMA Social Hub - Simple App Running", "timestamp": datetime.utcnow().isoformat()}

@app.get("/health")
async def health_check():
    """Health check endpoint for Render"""
    response = {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "service": "bma-social-simple",
        "version": "1.0.0"
    }
    logger.info(f"Health check called - responding with: {response}")
    return JSONResponse(status_code=200, content=response)

@app.get("/debug")
async def debug_info():
    """Debug endpoint to check environment"""
    return {
        "port": os.environ.get("PORT", "not_set"),
        "environment": os.environ.get("ENVIRONMENT", "not_set"),
        "python_version": sys.version,
        "cwd": os.getcwd(),
        "timestamp": datetime.utcnow().isoformat()
    }

if __name__ == "__main__":
    # Get port from environment (Render sets this)
    try:
        port = int(os.environ.get("PORT", 8000))
    except (ValueError, TypeError) as e:
        logger.error(f"Invalid PORT environment variable: {os.environ.get('PORT')} - using default 8000")
        port = 8000
        
    host = "0.0.0.0"
    
    logger.info(f"=== STARTING SERVER ===")
    logger.info(f"Host: {host}")
    logger.info(f"Port: {port}")
    logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'not_set')}")
    logger.info(f"All environment variables starting with 'PORT': {[k for k in os.environ.keys() if 'PORT' in k.upper()]}")
    
    # Double check we can create the health check response
    try:
        test_response = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "service": "bma-social-simple",
            "version": "1.0.0"
        }
        logger.info(f"Health check test response: {test_response}")
    except Exception as e:
        logger.error(f"Failed to create test response: {e}")
    
    try:
        # Start the server with minimal configuration
        logger.info("Starting uvicorn server...")
        uvicorn.run(
            app,
            host=host,
            port=port,
            log_level="info",
            access_log=True,
            workers=1,  # Single worker for simplicity
            timeout_keep_alive=30,
            timeout_graceful_shutdown=10
        )
    except Exception as e:
        logger.error(f"Failed to start server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)