"""Campaign model for managing outbound communications"""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Boolean, Integer, ForeignKey, Index, Enum, Text, DateTime
)
from sqlalchemy.dialects.postgresql import UUID, JSONB, ARRAY
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class CampaignStatus(PyEnum):
    """Campaign status enum"""
    DRAFT = "draft"
    SCHEDULED = "scheduled"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    CANCELLED = "cancelled"
    FAILED = "failed"


class CampaignType(PyEnum):
    """Campaign type enum"""
    MARKETING = "marketing"
    SERVICE = "service"
    HOLIDAY = "holiday"
    MAINTENANCE = "maintenance"
    SURVEY = "survey"
    ALERT = "alert"


class Campaign(BaseModel):
    """
    Campaign model for managing bulk outbound messages.
    Supports marketing, service updates, and automated communications.
    """
    
    __tablename__ = "campaigns"
    __table_args__ = (
        Index("idx_campaign_status_scheduled", "status", "scheduled_at"),
        Index("idx_campaign_type_status", "campaign_type", "status"),
        {"comment": "Outbound campaign management"}
    )
    
    # Campaign Details
    name = Column(String(255), nullable=False)
    campaign_type = Column(Enum(CampaignType), nullable=False, index=True)
    status = Column(Enum(CampaignStatus), default=CampaignStatus.DRAFT, nullable=False, index=True)
    
    # Scheduling
    scheduled_at = Column(DateTime(timezone=True), index=True)
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    
    # Targeting
    target_venues = Column(ARRAY(UUID(as_uuid=True)))  # Specific venue IDs
    target_brands = Column(JSONB, default=[])  # Brand filters
    target_countries = Column(JSONB, default=[])  # Country filters
    target_tags = Column(JSONB, default=[])  # Tag filters
    target_count = Column(Integer, default=0)  # Calculated target count
    
    # Content
    channel = Column(String(20), nullable=False)  # whatsapp, line, email
    message_template = Column(Text, nullable=False)
    message_variables = Column(JSONB, default={})  # Template variables
    media_url = Column(String(500))  # Image/document URL
    media_type = Column(String(50))  # image, document, video
    
    # Execution
    batch_size = Column(Integer, default=100)
    delay_between_batches = Column(Integer, default=1)  # Seconds
    retry_failed = Column(Boolean, default=True)
    max_retries = Column(Integer, default=3)
    
    # Metrics
    messages_sent = Column(Integer, default=0)
    messages_delivered = Column(Integer, default=0)
    messages_read = Column(Integer, default=0)
    messages_failed = Column(Integer, default=0)
    responses_received = Column(Integer, default=0)
    
    # Response Tracking
    track_responses = Column(Boolean, default=True)
    response_window_hours = Column(Integer, default=24)
    
    # Creator
    created_by = Column(UUID(as_uuid=True), ForeignKey("team_members.id"))
    approved_by = Column(UUID(as_uuid=True))
    approved_at = Column(DateTime(timezone=True))
    
    # Metadata
    metadata = Column(JSONB, default={})
    tags = Column(JSONB, default=[])
    
    # Relationships
    recipients = relationship("CampaignRecipient", back_populates="campaign", cascade="all, delete-orphan")
    
    @property
    def success_rate(self) -> float:
        """Calculate campaign success rate"""
        if self.messages_sent == 0:
            return 0.0
        return (self.messages_delivered / self.messages_sent) * 100
    
    @property
    def engagement_rate(self) -> float:
        """Calculate engagement rate"""
        if self.messages_delivered == 0:
            return 0.0
        return (self.responses_received / self.messages_delivered) * 100
    
    @property
    def is_active(self) -> bool:
        """Check if campaign is currently active"""
        return self.status == CampaignStatus.IN_PROGRESS
    
    def __repr__(self):
        return f"<Campaign(id={self.id}, name='{self.name}', type={self.campaign_type}, status={self.status})>"


class CampaignRecipient(BaseModel):
    """
    Campaign recipient tracking for detailed analytics.
    """
    
    __tablename__ = "campaign_recipients"
    __table_args__ = (
        Index("idx_recipient_campaign_venue", "campaign_id", "venue_id"),
        Index("idx_recipient_status", "status", "campaign_id"),
        {"comment": "Individual campaign recipient tracking"}
    )
    
    # Relationships
    campaign_id = Column(UUID(as_uuid=True), ForeignKey("campaigns.id"), nullable=False)
    campaign = relationship("Campaign", back_populates="recipients")
    
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=False)
    
    # Recipient Details
    recipient_phone = Column(String(50))
    recipient_email = Column(String(255))
    recipient_name = Column(String(255))
    channel = Column(String(20))
    
    # Delivery Status
    status = Column(String(50))  # pending, sent, delivered, read, failed
    sent_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    read_at = Column(DateTime(timezone=True))
    failed_at = Column(DateTime(timezone=True))
    failure_reason = Column(String(500))
    
    # Response
    responded = Column(Boolean, default=False)
    response_received_at = Column(DateTime(timezone=True))
    response_content = Column(Text)
    
    # Metadata
    metadata = Column(JSONB, default={})
    
    def __repr__(self):
        return f"<CampaignRecipient(id={self.id}, campaign_id={self.campaign_id}, status={self.status})>"