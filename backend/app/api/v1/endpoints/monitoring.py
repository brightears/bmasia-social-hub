"""Monitoring endpoints"""

from typing import Dict, Any
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db, db_manager
from app.core.redis import redis_manager
from app.services.soundtrack.client import soundtrack_client

router = APIRouter()


@router.get("/status")
async def get_monitoring_status() -> Dict[str, Any]:
    """Get overall monitoring status"""
    return {
        "monitoring": "active",
        "venues_monitored": 2000,
        "zones_monitored": 10000,
        "polling_interval": 300,
    }


@router.get("/metrics")
async def get_metrics() -> Dict[str, Any]:
    """Get system metrics"""
    
    # Get database metrics
    db_health = await db_manager.health_check()
    
    # Get Redis metrics
    redis_health = await redis_manager.health_check()
    
    # Get Soundtrack metrics
    soundtrack_metrics = await soundtrack_client.get_metrics()
    
    return {
        "database": db_health.get("performance_metrics"),
        "redis": redis_health.get("stats"),
        "soundtrack": soundtrack_metrics,
    }