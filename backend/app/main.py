"""
BMA Social FastAPI Application
Main entry point for the AI-powered music operations platform
"""

import logging
from contextlib import asynccontextmanager
from typing import Dict, Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException
from prometheus_client import make_asgi_app

from app.config import settings
from app.core.database import db_manager
from app.core.redis import redis_manager
from app.services.soundtrack.client import soundtrack_client
from app.api.v1.router import api_router
from app.api.v1.endpoints import health

# Configure logging
logging.basicConfig(
    level=getattr(logging, settings.log_level),
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Manage application lifecycle - startup and shutdown events
    """
    # Startup
    logger.info(f"Starting BMA Social API - Environment: {settings.environment}")
    
    try:
        # Initialize database with error handling
        try:
            db_manager.initialize()
            logger.info("Database initialized")
        except Exception as e:
            logger.warning(f"Database initialization failed (will retry on first request): {e}")
        
        # Initialize Redis with error handling
        try:
            redis_manager.initialize()
            logger.info("Redis initialized")
        except Exception as e:
            logger.warning(f"Redis initialization failed (will retry on first request): {e}")
        
        # Initialize Soundtrack client with error handling
        try:
            soundtrack_client.initialize()
            logger.info("Soundtrack API client initialized")
        except Exception as e:
            logger.warning(f"Soundtrack API client initialization failed (will retry on first request): {e}")
        
        # Initialize Sentry if configured
        if settings.sentry_dsn and settings.is_production:
            try:
                import sentry_sdk
                from sentry_sdk.integrations.fastapi import FastApiIntegration
                from sentry_sdk.integrations.sqlalchemy import SqlalchemyIntegration
                
                sentry_sdk.init(
                    dsn=settings.sentry_dsn,
                    environment=settings.environment,
                    integrations=[
                        FastApiIntegration(transaction_style="endpoint"),
                        SqlalchemyIntegration(),
                    ],
                    traces_sample_rate=0.1,  # 10% of transactions
                )
                logger.info("Sentry initialized")
            except Exception as e:
                logger.warning(f"Sentry initialization failed: {e}")
        
        logger.info("BMA Social API started successfully")
        
    except Exception as e:
        logger.error(f"Critical error during application startup: {e}")
        # Don't raise - let the app start even if some services fail
    
    yield
    
    # Shutdown
    logger.info("Shutting down BMA Social API...")
    
    try:
        # Close database connections
        try:
            db_manager.close()
            logger.info("Database connections closed")
        except Exception as e:
            logger.warning(f"Error closing database connections: {e}")
        
        # Close Redis connections
        try:
            redis_manager.close()
            logger.info("Redis connections closed")
        except Exception as e:
            logger.warning(f"Error closing Redis connections: {e}")
        
        # Close Soundtrack client
        try:
            soundtrack_client.close()
            logger.info("Soundtrack API client closed")
        except Exception as e:
            logger.warning(f"Error closing Soundtrack API client: {e}")
        
    except Exception as e:
        logger.error(f"Error during shutdown: {e}")
    
    logger.info("BMA Social API shutdown complete")


# Create FastAPI application
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="AI-powered music operations platform for 2000+ commercial venues",
    docs_url="/docs" if not settings.is_production else None,
    redoc_url="/redoc" if not settings.is_production else None,
    openapi_url="/openapi.json" if not settings.is_production else None,
    lifespan=lifespan,
)

# Add middleware

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["X-Total-Count", "X-Page", "X-Per-Page"],
)

# GZip compression
app.add_middleware(GZipMiddleware, minimum_size=1000)

# Trusted host middleware for production
if settings.is_production:
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=["*.bma-social.com", "*.onrender.com"],
    )

# Request ID middleware for tracking
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    """Add unique request ID for tracking"""
    import uuid
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    response = await call_next(request)
    response.headers["X-Request-ID"] = request_id
    return response

# Logging middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log all requests and responses"""
    import time
    
    # Skip logging for health check endpoints to reduce noise
    if request.url.path in ["/health", "/health/live", "/ready"]:
        return await call_next(request)
    
    start_time = time.time()
    
    # Log request
    logger.info(
        f"Request: {request.method} {request.url.path} "
        f"from {request.client.host if request.client else 'unknown'}"
    )
    
    try:
        response = await call_next(request)
        
        # Calculate duration
        duration = time.time() - start_time
        
        # Log response
        logger.info(
            f"Response: {response.status_code} for {request.method} {request.url.path} "
            f"(duration: {duration:.3f}s)"
        )
        
        # Add timing header
        response.headers["X-Response-Time"] = f"{duration:.3f}"
        
        return response
    except Exception as e:
        duration = time.time() - start_time
        logger.error(
            f"Error processing {request.method} {request.url.path} "
            f"(duration: {duration:.3f}s): {e}"
        )
        raise

# Rate limiting middleware (basic implementation)
from collections import defaultdict
from datetime import datetime, timedelta

rate_limit_storage = defaultdict(list)

@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    """Basic rate limiting middleware"""
    # Skip rate limiting for health check endpoints
    if request.url.path in ["/health", "/health/live", "/ready", "/health/detailed"]:
        return await call_next(request)
    
    if not settings.rate_limit_enabled:
        return await call_next(request)
    
    # Get client identifier
    client_id = request.client.host if request.client else "unknown"
    
    # Check rate limit
    now = datetime.utcnow()
    minute_ago = now - timedelta(minutes=1)
    
    # Clean old entries
    rate_limit_storage[client_id] = [
        timestamp for timestamp in rate_limit_storage[client_id]
        if timestamp > minute_ago
    ]
    
    # Check limit
    if len(rate_limit_storage[client_id]) >= settings.rate_limit_per_minute:
        return JSONResponse(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            content={"detail": "Rate limit exceeded. Please try again later."},
            headers={"Retry-After": "60"}
        )
    
    # Add current request
    rate_limit_storage[client_id].append(now)
    
    return await call_next(request)

# Exception handlers

@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(request: Request, exc: StarletteHTTPException):
    """Handle HTTP exceptions"""
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "detail": exc.detail,
            "status_code": exc.status_code,
            "request_id": getattr(request.state, "request_id", None),
        },
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle validation errors"""
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "detail": exc.errors(),
            "body": exc.body,
            "request_id": getattr(request.state, "request_id", None),
        },
    )

@app.exception_handler(Exception)
async def general_exception_handler(request: Request, exc: Exception):
    """Handle unexpected exceptions"""
    logger.error(f"Unexpected error: {exc}", exc_info=True)
    
    # Don't expose internal errors in production
    if settings.is_production:
        detail = "An internal error occurred. Please try again later."
    else:
        detail = str(exc)
    
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "detail": detail,
            "request_id": getattr(request.state, "request_id", None),
        },
    )

# Include API router
app.include_router(api_router, prefix="/api/v1")

# Root endpoint
@app.get("/", tags=["Root"])
def root() -> Dict[str, Any]:
    """Root endpoint"""
    return {
        "name": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "status": "operational",
        "message": "BMA Social API - AI-powered music operations platform",
    }

# Basic health check endpoint (at root level for Render)
# This endpoint is designed to respond quickly without checking dependencies
@app.get("/health", tags=["Health"])
def health_check() -> Dict[str, str]:
    """
    Basic health check endpoint for load balancers and monitoring.
    Used by Render for health checks. Returns quickly without checking dependencies.
    """
    return {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
    }

# Liveness check endpoint - simple check that the app is alive
@app.get("/health/live", tags=["Health"])
def liveness_check() -> Dict[str, str]:
    """
    Liveness check endpoint for container orchestration.
    Returns immediately to indicate the application process is alive.
    """
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat()
    }

# Readiness check endpoint - checks if the app is ready to serve traffic
@app.get("/ready", tags=["Health"])
async def readiness_check() -> Dict[str, Any]:
    """
    Readiness check endpoint to determine if the application is ready to serve traffic.
    Checks critical dependencies but with short timeouts.
    """
    import asyncio
    
    ready_status = {
        "ready": True,
        "version": settings.app_version,
        "checks": {}
    }
    
    # Quick database check with timeout
    try:
        from sqlalchemy import text
        with db_manager.get_session() as session:
            session.execute(text("SELECT 1"))
        ready_status["checks"]["database"] = "ready"
    except Exception:
        ready_status["checks"]["database"] = "not_ready"
        ready_status["ready"] = False
    
    # Quick Redis check with timeout (if initialized)
    try:
        if hasattr(redis_manager, 'redis') and redis_manager.redis:
            # Create a task with timeout
            redis_task = asyncio.create_task(redis_manager.redis.ping())
            await asyncio.wait_for(redis_task, timeout=2.0)
            ready_status["checks"]["redis"] = "ready"
    except (asyncio.TimeoutError, Exception):
        ready_status["checks"]["redis"] = "not_ready"
        # Redis is optional, don't fail readiness
    
    if ready_status["ready"]:
        return ready_status
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=ready_status
        )

# Detailed health check endpoint with dependency checks
@app.get("/health/detailed", tags=["Health"])
async def detailed_health_check() -> Dict[str, Any]:
    """
    Detailed health check endpoint that checks all dependencies.
    This may take longer and is suitable for debugging and detailed monitoring.
    """
    health_status = {
        "status": "healthy",
        "version": settings.app_version,
        "environment": settings.environment,
        "timestamp": datetime.utcnow().isoformat(),
        "checks": {},
    }
    
    # Check database
    try:
        db_health = db_manager.health_check()
        health_status["checks"]["database"] = db_health
    except Exception as e:
        health_status["checks"]["database"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
    
    # Check Redis (async)
    try:
        if hasattr(redis_manager, 'health_check'):
            redis_health = await redis_manager.health_check()
            health_status["checks"]["redis"] = redis_health
    except Exception as e:
        health_status["checks"]["redis"] = {"status": "unhealthy", "error": str(e)}
        health_status["status"] = "degraded"
    
    # Check Soundtrack API (async)
    try:
        if hasattr(soundtrack_client, 'health_check'):
            soundtrack_health = await soundtrack_client.health_check()
            health_status["checks"]["soundtrack"] = soundtrack_health
    except Exception as e:
        health_status["checks"]["soundtrack"] = {"status": "unhealthy", "error": str(e)}
        # Don't degrade overall health for external API issues
    
    # Return appropriate status code
    if health_status["status"] == "healthy":
        return health_status
    else:
        return JSONResponse(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            content=health_status
        )

# Metrics endpoint for Prometheus
if settings.prometheus_enabled:
    metrics_app = make_asgi_app()
    app.mount("/metrics", metrics_app)

# Application info endpoint
@app.get("/info", tags=["Info"])
def app_info() -> Dict[str, Any]:
    """Application information endpoint"""
    return {
        "app": {
            "name": settings.app_name,
            "version": settings.app_version,
            "environment": settings.environment,
        },
        "features": {
            "venues_supported": "2000+",
            "zones_monitored": "10,000+",
            "channels": ["WhatsApp", "Line", "Email"],
            "ai_powered": True,
            "real_time_monitoring": True,
        },
        "api": {
            "version": "v1",
            "docs_url": "/docs" if not settings.is_production else None,
            "openapi_url": "/openapi.json" if not settings.is_production else None,
        },
        "status": {
            "operational": True,
            "maintenance_mode": False,
        },
    }

if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.is_development,
        workers=settings.workers if not settings.is_development else 1,
        log_level=settings.log_level.lower(),
    )