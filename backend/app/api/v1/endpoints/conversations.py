"""Conversation management endpoints"""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import select

from app.core.database import get_db
from app.models.conversation import Conversation, ConversationStatus

router = APIRouter()


@router.get("/")
def get_conversations(
    status: Optional[ConversationStatus] = Query(None),
    venue_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """Get list of conversations with filters"""
    query = select(Conversation)
    
    if status:
        query = query.where(Conversation.status == status)
    
    if venue_id:
        query = query.where(Conversation.venue_id == venue_id)
    
    result = db.execute(
        query.offset(skip).limit(limit)
    )
    conversations = result.scalars().all()
    return conversations


@router.get("/{conversation_id}")
def get_conversation(
    conversation_id: str,
    db: Session = Depends(get_db)
):
    """Get specific conversation by ID"""
    result = db.execute(
        select(Conversation).where(Conversation.id == conversation_id)
    )
    conversation = result.scalar_one_or_none()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")
    
    return conversation