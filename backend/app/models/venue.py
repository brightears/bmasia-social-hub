"""Venue model for managing 2000+ commercial venues"""

from typing import List, Optional
from sqlalchemy import (
    Column, String, Boolean, Integer, Float, JSON, Index, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates

from app.models.base import BaseModel


class Venue(BaseModel):
    """
    Venue model representing hotels, restaurants, and retail locations.
    Optimized for 2000+ venues with complex metadata.
    """
    
    __tablename__ = "venues"
    __table_args__ = (
        Index("idx_venue_brand_country", "brand", "country"),
        Index("idx_venue_active_priority", "is_active", "priority"),
        Index("idx_venue_soundtrack_account", "soundtrack_account_id"),
        {"comment": "Commercial venues with background music subscriptions"}
    )
    
    # Basic Information
    name = Column(String(255), nullable=False, index=True)
    code = Column(String(50), unique=True, index=True)  # Internal venue code
    brand = Column(String(100), index=True)  # Hotel chain, restaurant brand
    venue_type = Column(String(50), nullable=False)  # hotel, restaurant, retail, spa
    
    # Location
    country = Column(String(2), nullable=False, index=True)  # ISO country code
    city = Column(String(100))
    address = Column(String(500))
    timezone = Column(String(50), nullable=False, default="UTC")
    latitude = Column(Float)
    longitude = Column(Float)
    
    # Soundtrack Integration
    soundtrack_account_id = Column(String(100), index=True)
    soundtrack_location_id = Column(String(100))
    
    # Contact Information
    primary_contact_name = Column(String(100))
    primary_contact_phone = Column(String(50))
    primary_contact_email = Column(String(255))
    it_contact_phone = Column(String(50))  # For technical alerts
    it_contact_email = Column(String(255))
    
    # Messaging Channels
    whatsapp_number = Column(String(50))
    line_user_id = Column(String(100))
    preferred_channel = Column(String(20), default="whatsapp")  # whatsapp, line, email
    language_preference = Column(String(10), default="en")  # en, th, ar, etc.
    
    # Operational Settings
    is_active = Column(Boolean, default=True, nullable=False, index=True)
    priority = Column(Integer, default=1)  # 1=standard, 2=premium, 3=VIP
    business_hours = Column(JSONB)  # {"mon": {"open": "09:00", "close": "22:00"}}
    
    # Music Preferences
    music_profile = Column(JSONB)  # Brand guidelines, volume limits, etc.
    auto_volume_enabled = Column(Boolean, default=False)
    weather_responsive = Column(Boolean, default=False)
    prayer_time_pause = Column(Boolean, default=False)  # For Middle East venues
    
    # Monitoring Settings
    monitoring_enabled = Column(Boolean, default=True)
    alert_threshold_minutes = Column(Integer, default=15)  # Minutes offline before alert
    alert_cooldown_minutes = Column(Integer, default=60)  # Minutes between alerts
    
    # Performance Metrics (Cached)
    total_zones = Column(Integer, default=0)
    active_zones = Column(Integer, default=0)
    last_month_uptime = Column(Float)  # Percentage
    last_month_satisfaction = Column(Float)  # Average score
    
    # Custom Metadata
    metadata = Column(JSONB, default={})  # Flexible field for custom data
    tags = Column(JSONB, default=[])  # ["vip", "high-traffic", "seasonal"]
    
    # Relationships
    zones = relationship("Zone", back_populates="venue", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="venue")
    satisfaction_scores = relationship("SatisfactionScore", back_populates="venue")
    
    @validates("country")
    def validate_country(self, key, value):
        """Ensure country code is uppercase"""
        return value.upper() if value else value
    
    @validates("priority")
    def validate_priority(self, key, value):
        """Ensure priority is within valid range"""
        if value not in [1, 2, 3]:
            raise ValueError("Priority must be 1 (standard), 2 (premium), or 3 (VIP)")
        return value
    
    @property
    def is_online(self) -> bool:
        """Check if venue has any online zones"""
        return self.active_zones > 0 if self.active_zones is not None else False
    
    @property
    def health_score(self) -> float:
        """Calculate overall health score (0-100)"""
        if not self.total_zones:
            return 0.0
        
        uptime_score = self.last_month_uptime if self.last_month_uptime else 0
        satisfaction_score = (self.last_month_satisfaction * 20) if self.last_month_satisfaction else 0
        zone_score = (self.active_zones / self.total_zones * 100) if self.total_zones else 0
        
        # Weighted average
        return (uptime_score * 0.4 + satisfaction_score * 0.3 + zone_score * 0.3)
    
    def get_contact_for_alert(self, alert_type: str = "technical") -> dict:
        """Get appropriate contact based on alert type"""
        if alert_type == "technical":
            return {
                "phone": self.it_contact_phone or self.primary_contact_phone,
                "email": self.it_contact_email or self.primary_contact_email,
                "channel": self.preferred_channel
            }
        else:
            return {
                "phone": self.primary_contact_phone,
                "email": self.primary_contact_email,
                "channel": self.preferred_channel
            }
    
    def __repr__(self):
        return f"<Venue(id={self.id}, name='{self.name}', brand='{self.brand}')>"