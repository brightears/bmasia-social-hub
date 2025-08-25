"""API v1 router configuration"""

from fastapi import APIRouter

from app.api.v1.endpoints import (
    webhooks,
    health,
    venues,
    zones,
    conversations,
    monitoring,
)

api_router = APIRouter()

# Include all endpoint routers
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks"])
api_router.include_router(health.router, prefix="/health", tags=["Health"])
api_router.include_router(venues.router, prefix="/venues", tags=["Venues"])
api_router.include_router(zones.router, prefix="/zones", tags=["Zones"])
api_router.include_router(conversations.router, prefix="/conversations", tags=["Conversations"])
api_router.include_router(monitoring.router, prefix="/monitoring", tags=["Monitoring"])