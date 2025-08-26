#!/usr/bin/env python
"""
Minimal startup script for Render deployment.
This script is designed to start immediately and bind to PORT without any blocking initialization.
All service initialization is deferred until first request.
"""

import os
import sys
import logging
import time
from datetime import datetime

# Configure basic logging immediately
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)
logger = logging.getLogger(__name__)

def log_startup_info():
    """Log essential startup information"""
    logger.info("="*50)
    logger.info("BMA Social API - Minimal Startup")
    logger.info("="*50)
    logger.info(f"Python version: {sys.version}")
    logger.info(f"Working directory: {os.getcwd()}")
    logger.info(f"Python path: {sys.executable}")
    logger.info(f"Current time: {datetime.utcnow().isoformat()}")
    
    # Log environment variables (sanitized)
    port = os.environ.get('PORT', 'NOT SET')
    database_url = 'SET' if os.environ.get('DATABASE_URL') else 'NOT SET'
    redis_url = 'SET' if os.environ.get('REDIS_URL') else 'NOT SET'
    environment = os.environ.get('ENVIRONMENT', 'NOT SET')
    
    logger.info(f"PORT env var: {port}")
    logger.info(f"DATABASE_URL env var: {database_url}")
    logger.info(f"REDIS_URL env var: {redis_url}")
    logger.info(f"ENVIRONMENT env var: {environment}")
    logger.info("="*50)

def create_minimal_app():
    """Create a minimal FastAPI app that starts immediately"""
    try:
        logger.info("Creating minimal FastAPI app...")
        
        from fastapi import FastAPI, Request
        from fastapi.responses import JSONResponse
        from fastapi.middleware.cors import CORSMiddleware
        import uvicorn
        
        # Create minimal app
        app = FastAPI(
            title="BMA Social API",
            version="1.0.0",
            description="AI-powered music operations platform",
            # Disable docs in production to speed up startup
            docs_url=None,
            redoc_url=None,
            openapi_url=None
        )
        
        # Add minimal CORS
        app.add_middleware(
            CORSMiddleware,
            allow_origins=["*"],  # Simplified for startup
            allow_methods=["GET", "POST"],
            allow_headers=["*"],
        )
        
        # Immediate health check endpoint (no dependencies)
        @app.get("/health")
        async def health_check():
            """Ultra-fast health check for Render"""
            return {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "startup": "minimal"
            }
        
        # Root endpoint
        @app.get("/")
        def root():
            return {
                "name": "BMA Social API",
                "status": "operational",
                "mode": "minimal_startup",
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Ready endpoint that will initialize services on first call
        @app.get("/ready")
        async def ready_check():
            """Readiness check that initializes services on demand"""
            try:
                # Import and initialize on first call only
                logger.info("Initializing services on demand...")
                
                # Try to import main app components
                from app.config import settings
                
                return {
                    "status": "ready",
                    "services": "initializing",
                    "timestamp": datetime.utcnow().isoformat()
                }
            except Exception as e:
                logger.error(f"Error in ready check: {e}")
                return JSONResponse(
                    status_code=503,
                    content={
                        "status": "not_ready",
                        "error": str(e),
                        "timestamp": datetime.utcnow().isoformat()
                    }
                )
        
        # Debug endpoint to show environment
        @app.get("/debug/env")
        async def debug_env():
            """Debug endpoint to show environment info"""
            return {
                "python_version": sys.version,
                "working_dir": os.getcwd(),
                "port": os.environ.get('PORT', 'NOT SET'),
                "environment": os.environ.get('ENVIRONMENT', 'NOT SET'),
                "database_configured": bool(os.environ.get('DATABASE_URL')),
                "redis_configured": bool(os.environ.get('REDIS_URL')),
                "timestamp": datetime.utcnow().isoformat()
            }
        
        logger.info("Minimal FastAPI app created successfully")
        return app
        
    except Exception as e:
        logger.error(f"Failed to create minimal app: {e}", exc_info=True)
        raise

# Create app instance for uvicorn (with error handling)
try:
    app = create_minimal_app()
except Exception as e:
    logger.error(f"Failed to create app instance: {e}")
    # Create an ultra-minimal fallback app
    from fastapi import FastAPI
    app = FastAPI()
    
    @app.get("/health")
    def health():
        return {"status": "healthy", "mode": "fallback"}
    
    @app.get("/")
    def root():
        return {"status": "operational", "mode": "fallback"}

def main():
    """Main entry point with immediate PORT binding"""
    try:
        log_startup_info()
        
        # Get PORT from environment (Render requires this)
        port = int(os.environ.get("PORT", 8000))
        logger.info(f"Using port: {port}")
        
        # Create minimal app
        app = create_minimal_app()
        
        # Import uvicorn
        import uvicorn
        
        logger.info("Starting uvicorn server...")
        logger.info(f"Server will bind to 0.0.0.0:{port}")
        
        # Start server with minimal configuration for fastest startup
        uvicorn.run(
            app,
            host="0.0.0.0",
            port=port,
            log_level="info",
            access_log=True,
            # Optimize for startup speed
            workers=1,  # Single worker for fast startup
            timeout_keep_alive=75,
            timeout_notify=30,
            # Disable reload in production
            reload=False,
            # Use minimal loop
            loop="asyncio",
        )
        
    except ImportError as e:
        logger.error(f"Import error during startup: {e}")
        logger.error("This usually means a dependency is missing or failed to install")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Critical startup error: {e}", exc_info=True)
        sys.exit(1)

if __name__ == "__main__":
    main()