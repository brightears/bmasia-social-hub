"""Zone management endpoints"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.core.database import get_db
from app.models.zone import Zone

router = APIRouter()


@router.get("/")
async def get_zones(
    venue_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db)
):
    """Get list of zones with optional venue filter"""
    query = select(Zone)
    
    if venue_id:
        query = query.where(Zone.venue_id == venue_id)
    
    result = await db.execute(
        query.offset(skip).limit(limit)
    )
    zones = result.scalars().all()
    return zones


@router.get("/{zone_id}")
async def get_zone(
    zone_id: str,
    db: AsyncSession = Depends(get_db)
):
    """Get specific zone by ID"""
    result = await db.execute(
        select(Zone).where(Zone.id == zone_id)
    )
    zone = result.scalar_one_or_none()
    
    if not zone:
        raise HTTPException(status_code=404, detail="Zone not found")
    
    return zone