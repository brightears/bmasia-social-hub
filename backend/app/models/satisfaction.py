"""Satisfaction score model for tracking customer feedback"""

from sqlalchemy import (
    Column, String, Integer, ForeignKey, Index, CheckConstraint, Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class SatisfactionScore(BaseModel):
    """
    Satisfaction score model for tracking customer feedback.
    Used for SLA compliance and service quality monitoring.
    """
    
    __tablename__ = "satisfaction_scores"
    __table_args__ = (
        Index("idx_satisfaction_venue_date", "venue_id", "created_at"),
        Index("idx_satisfaction_score", "score", "created_at"),
        CheckConstraint("score >= 1 AND score <= 5", name="check_satisfaction_score_range"),
        {"comment": "Customer satisfaction scores for conversations"}
    )
    
    # Relationships
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), unique=True, nullable=False)
    conversation = relationship("Conversation", back_populates="satisfaction_score")
    
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=False, index=True)
    venue = relationship("Venue", back_populates="satisfaction_scores")
    
    # Score Details
    score = Column(Integer, nullable=False)  # 1-5 rating
    feedback = Column(Text)  # Optional text feedback
    
    # Collection Method
    collection_method = Column(String(50))  # automated, manual, survey
    collection_channel = Column(String(50))  # whatsapp, line, email, web
    
    # Response Metadata
    response_time_seconds = Column(Integer)  # Time taken to provide feedback
    reminder_sent = Column(Integer, default=0)  # Number of reminders sent
    
    # Categories (for analysis)
    categories = Column(JSONB, default=[])  # ["response_time", "resolution", "bot_quality"]
    tags = Column(JSONB, default=[])  # Custom tags
    
    # Follow-up
    requires_followup = Column(String(20))  # yes, no, completed
    followup_notes = Column(Text)
    
    @property
    def is_positive(self) -> bool:
        """Check if score is positive (4 or 5)"""
        return self.score >= 4
    
    @property
    def is_negative(self) -> bool:
        """Check if score is negative (1 or 2)"""
        return self.score <= 2
    
    def __repr__(self):
        return f"<SatisfactionScore(id={self.id}, score={self.score}, venue_id={self.venue_id})>"