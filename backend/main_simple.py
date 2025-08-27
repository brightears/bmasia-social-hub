#!/usr/bin/env python3
"""
Simple FastAPI application - minimal dependencies, maximum reliability.
Gradually add features once core is stable.
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any

from fastapi import FastAPI, Response
from fastapi.responses import JSONResponse
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="BMA Social API",
    description="AI-powered music operations platform",
    version="0.1.0"
)

# Global state
startup_time = datetime.utcnow()
request_count = 0

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "BMA Social API",
        "status": "running",
        "mode": "simple",
        "uptime": str(datetime.utcnow() - startup_time)
    }

@app.get("/health")
async def health():
    """Health check endpoint - must return quickly for Render"""
    global request_count
    request_count += 1
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "uptime": str(datetime.utcnow() - startup_time),
        "requests_served": request_count
    }

@app.get("/api/v1/status")
async def api_status():
    """API status with more details"""
    return {
        "api_version": "1.0.0",
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "services": {
            "database": "not_connected",
            "redis": "not_connected",
            "soundtrack_api": "not_configured"
        },
        "features": {
            "venues": False,
            "zones": False,
            "conversations": False,
            "webhooks": False
        }
    }

@app.get("/api/v1/echo/{message}")
async def echo(message: str):
    """Simple echo endpoint for testing"""
    return {
        "echo": message,
        "timestamp": datetime.utcnow().isoformat()
    }

# Error handlers
@app.exception_handler(404)
async def not_found(request, exc):
    return JSONResponse(
        status_code=404,
        content={"error": "Not found", "path": str(request.url.path)}
    )

@app.exception_handler(500)
async def server_error(request, exc):
    logger.error(f"Internal error: {exc}")
    return JSONResponse(
        status_code=500,
        content={"error": "Internal server error"}
    )

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    
    logger.info("=" * 50)
    logger.info("Starting BMA Social API - Simple Mode")
    logger.info(f"Port: {port}")
    logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'development')}")
    logger.info("=" * 50)
    
    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )