"""Health check endpoints"""

from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, db_manager
from app.core.redis import redis_manager
from app.services.soundtrack.client import soundtrack_client

router = APIRouter()


@router.get("/status")
async def health_status() -> Dict[str, Any]:
    """Detailed health status of all services"""
    
    health = {
        "overall": "healthy",
        "services": {}
    }
    
    # Database health
    try:
        db_health = await db_manager.health_check()
        health["services"]["database"] = db_health
    except Exception as e:
        health["services"]["database"] = {"status": "error", "message": str(e)}
        health["overall"] = "degraded"
    
    # Redis health
    try:
        redis_health = await redis_manager.health_check()
        health["services"]["redis"] = redis_health
    except Exception as e:
        health["services"]["redis"] = {"status": "error", "message": str(e)}
        health["overall"] = "degraded"
    
    # Soundtrack API health
    try:
        soundtrack_health = await soundtrack_client.health_check()
        health["services"]["soundtrack"] = soundtrack_health
    except Exception as e:
        health["services"]["soundtrack"] = {"status": "error", "message": str(e)}
    
    return health


@router.get("/ready")
async def readiness_check(db: AsyncSession = Depends(get_db)) -> Dict[str, str]:
    """Readiness probe for Kubernetes/container orchestration"""
    
    # Check if database is accessible
    await db.execute("SELECT 1")
    
    # Check if Redis is accessible
    await redis_manager.redis.ping()
    
    return {"status": "ready"}


@router.get("/live")
async def liveness_check() -> Dict[str, str]:
    """Liveness probe for Kubernetes/container orchestration"""
    return {"status": "alive"}