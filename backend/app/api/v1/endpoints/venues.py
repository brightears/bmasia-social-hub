"""Venue management endpoints"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.models.venue import Venue

router = APIRouter()


@router.get("/")
def get_venues(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get list of venues with pagination"""
    result = db.execute(
        select(Venue)
        .offset(skip)
        .limit(limit)
    )
    venues = result.scalars().all()
    return venues


@router.get("/{venue_id}")
def get_venue(
    venue_id: str,
    db: Session = Depends(get_db)
):
    """Get specific venue by ID"""
    result = db.execute(
        select(Venue).where(Venue.id == venue_id)
    )
    venue = result.scalar_one_or_none()
    
    if not venue:
        raise HTTPException(status_code=404, detail="Venue not found")
    
    return venue