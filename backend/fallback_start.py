#!/usr/bin/env python
"""
Fallback startup script for Render deployment.
This script creates the most minimal possible FastAPI app that will start.
Use this if minimal_start.py still has issues.
"""

import os
import sys
import logging
from datetime import datetime

# Ultra-minimal logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

def create_ultra_minimal_app():
    """Create the most minimal FastAPI app possible"""
    logger.info("Creating ultra-minimal FastAPI app...")
    
    from fastapi import FastAPI
    
    # Absolute minimal app
    app = FastAPI(
        title="BMA Social API",
        docs_url=None,
        redoc_url=None,
        openapi_url=None
    )
    
    @app.get("/health")
    def health():
        return {"status": "healthy", "timestamp": datetime.utcnow().isoformat()}
    
    @app.get("/")
    def root():
        return {"status": "operational", "service": "BMA Social API"}
    
    logger.info("Ultra-minimal app created")
    return app

def main():
    """Ultra-minimal startup"""
    logger.info("BMA Social API - Fallback Startup")
    logger.info(f"PORT: {os.environ.get('PORT', 'NOT SET')}")
    logger.info(f"Python: {sys.version}")
    
    try:
        app = create_ultra_minimal_app()
        port = int(os.environ.get("PORT", 8000))
        
        import uvicorn
        logger.info(f"Starting uvicorn on port {port}")
        
        uvicorn.run(
            app,
            host="0.0.0.0", 
            port=port,
            log_level="info"
        )
    except Exception as e:
        logger.error(f"Fallback startup failed: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()