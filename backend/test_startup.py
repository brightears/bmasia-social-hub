#!/usr/bin/env python
"""
Startup diagnostic script to test different startup methods.
Run this locally or on Render to see which approach works best.
"""

import os
import sys
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_environment():
    """Test environment setup"""
    logger.info("="*50)
    logger.info("STARTUP DIAGNOSTICS")
    logger.info("="*50)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Python executable: {sys.executable}")
    logger.info(f"PORT env var: {os.environ.get('PORT', 'NOT SET')}")
    logger.info(f"Environment: {os.environ.get('ENVIRONMENT', 'NOT SET')}")
    logger.info("="*50)

def test_basic_imports():
    """Test basic Python imports"""
    logger.info("Testing basic imports...")
    
    try:
        import fastapi
        logger.info(f"✓ FastAPI version: {fastapi.__version__}")
    except ImportError as e:
        logger.error(f"✗ FastAPI import failed: {e}")
        return False
    
    try:
        import uvicorn
        logger.info(f"✓ uvicorn imported successfully")
    except ImportError as e:
        logger.error(f"✗ uvicorn import failed: {e}")
        return False
    
    try:
        import sqlalchemy
        logger.info(f"✓ SQLAlchemy version: {sqlalchemy.__version__}")
    except ImportError as e:
        logger.error(f"✗ SQLAlchemy import failed: {e}")
        return False
    
    try:
        import psycopg2
        logger.info(f"✓ psycopg2 imported successfully")
    except ImportError as e:
        logger.error(f"✗ psycopg2 import failed: {e}")
        return False
    
    logger.info("All basic imports successful!")
    return True

def test_app_imports():
    """Test application-specific imports"""
    logger.info("Testing application imports...")
    
    try:
        from app.config import settings
        logger.info(f"✓ Config imported (env: {settings.environment})")
    except Exception as e:
        logger.error(f"✗ Config import failed: {e}")
        return False
    
    try:
        from app.main import app
        logger.info("✓ Main app imported successfully")
    except Exception as e:
        logger.error(f"✗ Main app import failed: {e}")
        return False
    
    logger.info("All app imports successful!")
    return True

def test_minimal_server():
    """Test starting a minimal server"""
    logger.info("Testing minimal server startup...")
    
    try:
        from fastapi import FastAPI
        import uvicorn
        
        app = FastAPI()
        
        @app.get("/test")
        def test():
            return {"status": "test_ok"}
        
        port = int(os.environ.get("PORT", 8001))  # Use different port for testing
        logger.info(f"Would start server on port {port}")
        
        # Don't actually start the server, just test the setup
        logger.info("✓ Minimal server setup successful")
        return True
        
    except Exception as e:
        logger.error(f"✗ Minimal server test failed: {e}")
        return False

def main():
    """Run all diagnostic tests"""
    test_environment()
    
    if not test_basic_imports():
        logger.error("DIAGNOSIS: Basic imports failed - check dependencies")
        sys.exit(1)
    
    if not test_app_imports():
        logger.error("DIAGNOSIS: App imports failed - use minimal startup")
        logger.info("RECOMMENDATION: Use fallback_start.py")
        sys.exit(1)
    
    if not test_minimal_server():
        logger.error("DIAGNOSIS: Server setup failed")
        sys.exit(1)
    
    logger.info("="*50)
    logger.info("ALL TESTS PASSED!")
    logger.info("RECOMMENDATION: Full app startup should work")
    logger.info("Try: python minimal_start.py")
    logger.info("="*50)

if __name__ == "__main__":
    main()