#!/usr/bin/env python
"""
Debug startup script for full application testing.
Use minimal_start.py for production Render deployment.
"""

import os
import sys
import logging
from datetime import datetime

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def log_environment():
    """Log detailed environment information"""
    logger.info("="*60)
    logger.info("BMA Social API - Debug Startup")
    logger.info("="*60)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Python path: {':'.join(sys.path[:5])}...")
    
    # Environment variables
    logger.info("Environment Variables:")
    logger.info(f"  PORT: {os.environ.get('PORT', 'NOT SET')}")
    logger.info(f"  ENVIRONMENT: {os.environ.get('ENVIRONMENT', 'NOT SET')}")
    logger.info(f"  DATABASE_URL: {'SET' if os.environ.get('DATABASE_URL') else 'NOT SET'}")
    logger.info(f"  REDIS_URL: {'SET' if os.environ.get('REDIS_URL') else 'NOT SET'}")
    logger.info(f"  SECRET_KEY: {'SET' if os.environ.get('SECRET_KEY') else 'NOT SET'}")
    logger.info(f"  JWT_SECRET_KEY: {'SET' if os.environ.get('JWT_SECRET_KEY') else 'NOT SET'}")
    
    logger.info(f"Current time: {datetime.utcnow().isoformat()}")
    logger.info("="*60)

def test_imports():
    """Test critical imports step by step"""
    try:
        logger.info("Testing imports...")
        
        logger.info("1. Testing FastAPI import...")
        from fastapi import FastAPI
        logger.info("   ✓ FastAPI imported successfully")
        
        logger.info("2. Testing uvicorn import...")
        import uvicorn
        logger.info("   ✓ uvicorn imported successfully")
        
        logger.info("3. Testing app.config import...")
        from app.config import settings
        logger.info(f"   ✓ Config imported successfully (env: {settings.environment})")
        
        logger.info("4. Testing app.main import...")
        from app.main import app
        logger.info("   ✓ Main app imported successfully")
        
        logger.info("All imports successful!")
        return app
        
    except Exception as e:
        logger.error(f"Import failed: {e}", exc_info=True)
        return None

def main():
    """Main debug startup function"""
    try:
        log_environment()
        
        # Test imports
        app = test_imports()
        if app is None:
            logger.error("Cannot start - import failed")
            sys.exit(1)
        
        # Get port
        port = int(os.environ.get('PORT', 8000))
        logger.info(f"Starting server on port {port}")
        
        # Start uvicorn with debug configuration
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True,
            reload=False,  # Don't use reload in production
            workers=1,     # Single worker for debugging
            timeout_keep_alive=30,
        )
        
    except KeyboardInterrupt:
        logger.info("Shutdown requested by user")
    except Exception as e:
        logger.error(f"Failed to start: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()