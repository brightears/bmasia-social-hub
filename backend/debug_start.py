#!/usr/bin/env python
"""Debug startup script to diagnose deployment issues"""

import os
import sys
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

logger.info(f"Python version: {sys.version}")
logger.info(f"Working directory: {os.getcwd()}")
logger.info(f"PORT env var: {os.environ.get('PORT', 'NOT SET')}")
logger.info(f"DATABASE_URL env var: {'SET' if os.environ.get('DATABASE_URL') else 'NOT SET'}")
logger.info(f"REDIS_URL env var: {'SET' if os.environ.get('REDIS_URL') else 'NOT SET'}")

# Try importing the app
try:
    logger.info("Importing app.main...")
    from app.main import app
    logger.info("App imported successfully")
    
    # Try to start uvicorn
    import uvicorn
    port = int(os.environ.get('PORT', 8000))
    logger.info(f"Starting uvicorn on port {port}")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info",
        access_log=True
    )
except Exception as e:
    logger.error(f"Failed to start: {e}", exc_info=True)
    sys.exit(1)