"""Team member model for internal user management"""

from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Boolean, Index, Enum, DateTime, Integer, Float
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates
import re

from app.models.base import BaseModel


class TeamRole(PyEnum):
    """Team member roles"""
    ADMIN = "admin"
    MANAGER = "manager"
    SUPPORT = "support"
    VIEWER = "viewer"


class TeamMember(BaseModel):
    """
    Team member model for BMAsia staff.
    Manages permissions and conversation assignments.
    """
    
    __tablename__ = "team_members"
    __table_args__ = (
        Index("idx_team_member_email", "email"),
        Index("idx_team_member_active_role", "is_active", "role"),
        {"comment": "BMAsia team members with role-based permissions"}
    )
    
    # Basic Information
    email = Column(String(255), unique=True, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    phone = Column(String(50))
    avatar_url = Column(String(500))
    
    # Authentication
    password_hash = Column(String(255))  # Hashed password
    
    # Role and Permissions
    role = Column(Enum(TeamRole), nullable=False, default=TeamRole.SUPPORT)
    permissions = Column(JSONB, default={})  # Granular permissions
    
    # Status
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    is_online = Column(Boolean, default=False)
    last_seen_at = Column(DateTime(timezone=True))
    
    # Work Assignment
    max_conversations = Column(Integer, default=10)  # Max concurrent conversations
    current_conversation_count = Column(Integer, default=0)
    specializations = Column(JSONB, default=[])  # ["technical", "billing", "vip"]
    language_skills = Column(JSONB, default=["en"])  # ["en", "th", "ar"]
    
    # Performance Metrics (Cached)
    total_conversations_handled = Column(Integer, default=0)
    avg_response_time_seconds = Column(Integer)
    avg_resolution_time_seconds = Column(Integer)
    avg_satisfaction_score = Column(Float)
    
    # Availability
    working_hours = Column(JSONB, default={})  # Schedule per day
    timezone = Column(String(50), default="UTC")
    on_vacation = Column(Boolean, default=False)
    vacation_end_date = Column(DateTime(timezone=True))
    
    # Notifications
    notification_preferences = Column(JSONB, default={
        "email": True,
        "slack": False,
        "sms": False
    })
    
    # Metadata
    metadata = Column(JSONB, default={})
    tags = Column(JSONB, default=[])
    
    # Relationships
    conversations = relationship("Conversation", back_populates="assigned_team")
    
    @validates("email")
    def validate_email(self, key, value):
        """Validate email format"""
        if not re.match(r"[^@]+@[^@]+\.[^@]+", value):
            raise ValueError("Invalid email format")
        return value.lower()
    
    @validates("role")
    def validate_role_permissions(self, key, value):
        """Set default permissions based on role"""
        default_permissions = {
            TeamRole.ADMIN: {
                "manage_team": True,
                "manage_venues": True,
                "view_analytics": True,
                "handle_conversations": True,
                "create_campaigns": True,
                "system_settings": True
            },
            TeamRole.MANAGER: {
                "manage_team": False,
                "manage_venues": True,
                "view_analytics": True,
                "handle_conversations": True,
                "create_campaigns": True,
                "system_settings": False
            },
            TeamRole.SUPPORT: {
                "manage_team": False,
                "manage_venues": False,
                "view_analytics": False,
                "handle_conversations": True,
                "create_campaigns": False,
                "system_settings": False
            },
            TeamRole.VIEWER: {
                "manage_team": False,
                "manage_venues": False,
                "view_analytics": True,
                "handle_conversations": False,
                "create_campaigns": False,
                "system_settings": False
            }
        }
        
        if not self.permissions:
            self.permissions = default_permissions.get(value, {})
        
        return value
    
    @property
    def is_available(self) -> bool:
        """Check if team member is available for new conversations"""
        return (
            self.is_active and
            self.is_online and
            not self.on_vacation and
            self.current_conversation_count < self.max_conversations
        )
    
    @property
    def capacity_percentage(self) -> float:
        """Calculate current capacity usage"""
        if self.max_conversations == 0:
            return 0.0
        return (self.current_conversation_count / self.max_conversations) * 100
    
    def can_handle_conversation(self, conversation) -> bool:
        """Check if team member can handle a specific conversation"""
        if not self.is_available:
            return False
        
        # Check language match
        if conversation.language not in self.language_skills:
            return False
        
        # Check specialization match
        if conversation.category in ["technical", "billing", "vip"]:
            if conversation.category not in self.specializations:
                return False
        
        return True
    
    def __repr__(self):
        return f"<TeamMember(id={self.id}, email='{self.email}', role={self.role})>"