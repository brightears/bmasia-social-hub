#!/usr/bin/env python3
"""
FastAPI application with database connection
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional

from fastapi import FastAPI, Response, Depends, HTTPException
from fastapi.responses import JSONResponse
import uvicorn

# Try to import psycopg2, but make it optional
try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    HAS_DATABASE = True
except ImportError:
    HAS_DATABASE = False
    psycopg2 = None
    RealDictCursor = None

# Try to import redis, but make it optional
try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False
    redis = None

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Create FastAPI app
app = FastAPI(
    title="BMA Social API",
    description="AI-powered music operations platform with database",
    version="0.2.0"
)

# Global state
startup_time = datetime.utcnow()
request_count = 0
db_connection = None
redis_client = None

def get_db_connection():
    """Get database connection"""
    global db_connection
    
    if not HAS_DATABASE:
        logger.warning("psycopg2 not installed - database features disabled")
        return None
    
    DATABASE_URL = os.environ.get('DATABASE_URL', 
        'postgresql://bma_user:wVLGYkim3mf3qYocucd6IhXjogfLbZAb@dpg-d2m6jrre5dus739fr8p0-a/bma_social_esoq')
    
    try:
        if db_connection is None or db_connection.closed:
            db_connection = psycopg2.connect(DATABASE_URL)
            logger.info("Database connected successfully")
        return db_connection
    except Exception as e:
        logger.error(f"Database connection failed: {e}")
        return None

def get_redis_client():
    """Get Redis client"""
    global redis_client
    
    if not HAS_REDIS:
        logger.warning("redis not installed - cache features disabled")
        return None
    
    REDIS_URL = os.environ.get('REDIS_URL', 
        'redis://red-d2m6jrre5dus739fr8g0:6379')
    
    try:
        if redis_client is None:
            redis_client = redis.from_url(REDIS_URL, decode_responses=True)
            # Test connection
            redis_client.ping()
            logger.info("Redis connected successfully")
        return redis_client
    except Exception as e:
        logger.error(f"Redis connection failed: {e}")
        redis_client = None
        return None

@app.on_event("startup")
async def startup_event():
    """Initialize on startup"""
    logger.info("Starting BMA Social API with Database and Cache")
    
    # Initialize database
    conn = get_db_connection()
    if conn:
        logger.info("✅ Database connection established")
    else:
        logger.warning("⚠️ Running without database")
    
    # Initialize Redis
    redis = get_redis_client()
    if redis:
        logger.info("✅ Redis connection established")
    else:
        logger.warning("⚠️ Running without cache")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global db_connection
    if db_connection and not db_connection.closed:
        db_connection.close()
        logger.info("Database connection closed")

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "BMA Social API",
        "status": "running",
        "mode": "with_database",
        "uptime": str(datetime.utcnow() - startup_time)
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
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
    """API status with database and cache check"""
    db_status = "connected"
    redis_status = "connected"
    table_count = 0
    
    # Check database
    conn = get_db_connection()
    if conn:
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT COUNT(*) FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            table_count = cursor.fetchone()[0]
            cursor.close()
        except Exception as e:
            db_status = f"error: {str(e)}"
    else:
        db_status = "not_connected"
    
    # Check Redis
    redis = get_redis_client()
    if redis:
        try:
            redis.ping()
            redis_status = "connected"
        except Exception as e:
            redis_status = f"error: {str(e)}"
    else:
        redis_status = "not_connected"
    
    return {
        "api_version": "2.0.0",
        "environment": os.environ.get("ENVIRONMENT", "development"),
        "services": {
            "database": db_status,
            "database_tables": table_count,
            "redis": redis_status,
            "soundtrack_api": "not_configured"
        },
        "features": {
            "venues": table_count > 0,
            "zones": table_count > 0,
            "conversations": False,
            "webhooks": False
        }
    }

@app.get("/api/v1/database/test")
async def test_database():
    """Test database connection"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor) if RealDictCursor else conn.cursor()
        
        # Get PostgreSQL version
        cursor.execute("SELECT version();")
        version = cursor.fetchone()
        
        # Get database size
        cursor.execute("""
            SELECT pg_database_size(current_database()) as size_bytes,
                   pg_size_pretty(pg_database_size(current_database())) as size_pretty
        """)
        db_size = cursor.fetchone()
        
        # Get table list
        cursor.execute("""
            SELECT table_name, 
                   pg_size_pretty(pg_total_relation_size(quote_ident(table_name))) as size
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            ORDER BY table_name
        """)
        tables = cursor.fetchall()
        
        cursor.close()
        
        return {
            "status": "connected",
            "postgresql_version": version['version'],
            "database_size": db_size['size_pretty'],
            "tables": tables
        }
        
    except Exception as e:
        logger.error(f"Database test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/v1/database/init")
async def init_database():
    """Initialize database with basic tables"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        cursor = conn.cursor()
        
        # Create venues table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS venues (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                location VARCHAR(500),
                soundtrack_account_id VARCHAR(255),
                active BOOLEAN DEFAULT true,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create zones table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS zones (
                id SERIAL PRIMARY KEY,
                venue_id INTEGER REFERENCES venues(id) ON DELETE CASCADE,
                name VARCHAR(255) NOT NULL,
                soundtrack_zone_id VARCHAR(255),
                status VARCHAR(50) DEFAULT 'unknown',
                last_check TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create alerts table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS alerts (
                id SERIAL PRIMARY KEY,
                zone_id INTEGER REFERENCES zones(id) ON DELETE CASCADE,
                alert_type VARCHAR(50),
                message TEXT,
                resolved BOOLEAN DEFAULT false,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                resolved_at TIMESTAMP
            )
        """)
        
        conn.commit()
        cursor.close()
        
        return {
            "status": "success",
            "message": "Database initialized with basic tables",
            "tables_created": ["venues", "zones", "alerts"]
        }
        
    except Exception as e:
        conn.rollback()
        logger.error(f"Database init failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/cache/test")
async def test_cache():
    """Test Redis cache connection"""
    redis = get_redis_client()
    if not redis:
        raise HTTPException(status_code=503, detail="Cache not available")
    
    try:
        # Set a test key
        test_key = f"test_{datetime.utcnow().timestamp()}"
        redis.set(test_key, "Hello Redis!", ex=60)  # Expire after 60 seconds
        
        # Get the test key
        value = redis.get(test_key)
        
        # Get Redis info
        info = redis.info()
        
        return {
            "status": "connected",
            "test_key": test_key,
            "test_value": value,
            "redis_version": info.get("redis_version", "unknown"),
            "used_memory_human": info.get("used_memory_human", "unknown"),
            "connected_clients": info.get("connected_clients", 0),
            "total_commands_processed": info.get("total_commands_processed", 0)
        }
        
    except Exception as e:
        logger.error(f"Cache test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/api/v1/venues")
async def get_venues():
    """Get all venues"""
    conn = get_db_connection()
    if not conn:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        cursor = conn.cursor(cursor_factory=RealDictCursor) if RealDictCursor else conn.cursor()
        cursor.execute("SELECT * FROM venues ORDER BY id")
        venues = cursor.fetchall()
        cursor.close()
        
        return {
            "count": len(venues),
            "venues": venues
        }
    except Exception as e:
        if "venues" not in str(e):
            logger.error(f"Failed to get venues: {e}")
        return {
            "count": 0,
            "venues": [],
            "error": "Table not initialized. Call /api/v1/database/init first"
        }

# Add webhook routes
try:
    from app.api.v1.endpoints import webhooks
    app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
    logger.info("Webhook routes loaded successfully")
except ImportError as e:
    logger.warning(f"Could not load webhook routes: {e}")

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
    logger.info("Starting BMA Social API - Database Mode")
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