"""Conversation and Message models for multi-channel support"""

from datetime import datetime, timedelta
from typing import Optional
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Boolean, Integer, Float, ForeignKey, Index, Enum, Text, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates

from app.models.base import BaseModel


class ConversationStatus(PyEnum):
    """Conversation status enum"""
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    WAITING_CUSTOMER = "waiting_customer"
    WAITING_TEAM = "waiting_team"
    RESOLVED = "resolved"
    CLOSED = "closed"


class ConversationChannel(PyEnum):
    """Communication channel enum"""
    WHATSAPP = "whatsapp"
    LINE = "line"
    EMAIL = "email"
    WEB = "web"
    INTERNAL = "internal"


class MessageSenderType(PyEnum):
    """Message sender type enum"""
    CUSTOMER = "customer"
    BOT = "bot"
    TEAM = "team"
    SYSTEM = "system"


class ConversationPriority(PyEnum):
    """Conversation priority enum"""
    LOW = "low"
    NORMAL = "normal"
    HIGH = "high"
    URGENT = "urgent"


class Conversation(BaseModel):
    """
    Conversation model for tracking all customer interactions.
    Supports WhatsApp, Line, Email with SLA tracking.
    """
    
    __tablename__ = "conversations"
    __table_args__ = (
        Index("idx_conversation_venue_status", "venue_id", "status"),
        Index("idx_conversation_channel_status", "channel", "status"),
        Index("idx_conversation_assigned", "assigned_to", "status"),
        Index("idx_conversation_sla", "sla_deadline", "status"),
        Index("idx_conversation_external", "external_id", "channel"),
        {"comment": "Customer conversations across all channels"}
    )
    
    # Relationships
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=False, index=True)
    venue = relationship("Venue", back_populates="conversations")
    
    # Channel Information
    channel = Column(Enum(ConversationChannel), nullable=False, index=True)
    external_id = Column(String(255))  # WhatsApp/Line conversation ID
    customer_phone = Column(String(50))
    customer_email = Column(String(255))
    customer_name = Column(String(255))
    customer_id = Column(String(100))  # External platform user ID
    
    # Status and Assignment
    status = Column(Enum(ConversationStatus), default=ConversationStatus.OPEN, nullable=False, index=True)
    priority = Column(Enum(ConversationPriority), default=ConversationPriority.NORMAL, nullable=False, index=True)
    assigned_to = Column(UUID(as_uuid=True), ForeignKey("team_members.id"), index=True)
    assigned_at = Column(DateTime(timezone=True))
    assigned_team = relationship("TeamMember", back_populates="conversations")
    
    # Conversation Context
    subject = Column(String(500))
    category = Column(String(100))  # music_control, technical_issue, billing, general
    subcategory = Column(String(100))  # volume_adjustment, playlist_change, device_offline
    language = Column(String(10), default="en")
    
    # SLA Tracking
    sla_deadline = Column(DateTime(timezone=True), index=True)
    first_response_at = Column(DateTime(timezone=True))
    first_response_time_seconds = Column(Integer)  # Time to first response
    resolution_time_seconds = Column(Integer)  # Total resolution time
    resolved_at = Column(DateTime(timezone=True))
    closed_at = Column(DateTime(timezone=True))
    
    # Bot Handling
    bot_handled = Column(Boolean, default=False)
    bot_confidence_score = Column(Float)  # 0-1 confidence in bot's ability to handle
    bot_escalated = Column(Boolean, default=False)
    bot_escalation_reason = Column(String(500))
    
    # Metrics
    message_count = Column(Integer, default=0)
    customer_message_count = Column(Integer, default=0)
    team_message_count = Column(Integer, default=0)
    bot_message_count = Column(Integer, default=0)
    
    # Satisfaction
    satisfaction_requested = Column(Boolean, default=False)
    satisfaction_requested_at = Column(DateTime(timezone=True))
    
    # Metadata
    metadata = Column(JSONB, default={})
    tags = Column(JSONB, default=[])  # ["vip", "complaint", "urgent"]
    
    # Session Management
    session_id = Column(String(100))  # For maintaining context
    last_activity_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    
    # Relationships
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan", order_by="Message.created_at")
    satisfaction_score = relationship("SatisfactionScore", back_populates="conversation", uselist=False)
    
    @validates("priority")
    def validate_priority_based_on_tags(self, key, value):
        """Auto-set priority based on tags"""
        if "vip" in (self.tags or []):
            return ConversationPriority.HIGH
        if "urgent" in (self.tags or []):
            return ConversationPriority.URGENT
        return value
    
    @property
    def is_overdue(self) -> bool:
        """Check if conversation has exceeded SLA"""
        if not self.sla_deadline or self.status in [ConversationStatus.RESOLVED, ConversationStatus.CLOSED]:
            return False
        return datetime.utcnow() > self.sla_deadline
    
    @property
    def response_time_status(self) -> str:
        """Get SLA status"""
        if self.status in [ConversationStatus.RESOLVED, ConversationStatus.CLOSED]:
            if self.first_response_time_seconds:
                if self.first_response_time_seconds < 60:  # Under 1 minute
                    return "excellent"
                elif self.first_response_time_seconds < 300:  # Under 5 minutes
                    return "good"
                elif self.first_response_time_seconds < 3600:  # Under 1 hour
                    return "acceptable"
                else:
                    return "poor"
        elif self.is_overdue:
            return "overdue"
        return "in_progress"
    
    @property
    def requires_human_intervention(self) -> bool:
        """Check if conversation needs human attention"""
        return (
            self.bot_escalated or
            self.bot_confidence_score and self.bot_confidence_score < 0.7 or
            self.priority in [ConversationPriority.HIGH, ConversationPriority.URGENT] or
            self.is_overdue
        )
    
    def calculate_sla_deadline(self) -> datetime:
        """Calculate SLA deadline based on priority"""
        deadlines = {
            ConversationPriority.URGENT: timedelta(minutes=15),
            ConversationPriority.HIGH: timedelta(hours=1),
            ConversationPriority.NORMAL: timedelta(hours=4),
            ConversationPriority.LOW: timedelta(hours=24),
        }
        return datetime.utcnow() + deadlines.get(self.priority, timedelta(hours=4))
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, venue_id={self.venue_id}, channel={self.channel}, status={self.status})>"


class Message(BaseModel):
    """
    Message model for storing all conversation messages.
    Optimized for high-volume messaging with metadata support.
    """
    
    __tablename__ = "messages"
    __table_args__ = (
        Index("idx_message_conversation", "conversation_id", "created_at"),
        Index("idx_message_sender", "sender_type", "created_at"),
        {"comment": "Individual messages within conversations"}
    )
    
    # Relationships
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True)
    conversation = relationship("Conversation", back_populates="messages")
    
    # Message Details
    sender_type = Column(Enum(MessageSenderType), nullable=False, index=True)
    sender_id = Column(String(255))  # User ID, team member ID, or "bot"
    sender_name = Column(String(255))
    
    # Content
    content = Column(Text, nullable=False)
    content_type = Column(String(50), default="text")  # text, image, document, audio, location
    
    # Attachments
    attachment_url = Column(String(500))
    attachment_name = Column(String(255))
    attachment_size = Column(Integer)  # Bytes
    attachment_type = Column(String(100))  # MIME type
    
    # Message Metadata
    external_id = Column(String(255))  # WhatsApp/Line message ID
    reply_to_id = Column(UUID(as_uuid=True))  # For threaded messages
    
    # Bot Processing
    intent = Column(String(100))  # Detected intent
    entities = Column(JSONB)  # Extracted entities
    sentiment = Column(String(20))  # positive, negative, neutral
    confidence_score = Column(Float)  # Bot confidence in understanding
    
    # Actions Taken
    actions = Column(JSONB)  # [{"type": "volume_change", "details": {...}}]
    action_results = Column(JSONB)  # Results of automated actions
    
    # Status
    is_read = Column(Boolean, default=False)
    read_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    failed_delivery = Column(Boolean, default=False)
    failure_reason = Column(String(500))
    
    # Metadata
    metadata = Column(JSONB, default={})
    
    @validates("content_type")
    def validate_content_type(self, key, value):
        """Validate content type"""
        valid_types = ["text", "image", "document", "audio", "video", "location", "sticker", "template"]
        if value not in valid_types:
            raise ValueError(f"Content type must be one of: {valid_types}")
        return value
    
    @property
    def is_automated(self) -> bool:
        """Check if message was automated"""
        return self.sender_type in [MessageSenderType.BOT, MessageSenderType.SYSTEM]
    
    @property
    def requires_translation(self) -> bool:
        """Check if message might need translation"""
        return self.conversation.language != "en" and self.sender_type == MessageSenderType.CUSTOMER
    
    def __repr__(self):
        return f"<Message(id={self.id}, conversation_id={self.conversation_id}, sender_type={self.sender_type})>"