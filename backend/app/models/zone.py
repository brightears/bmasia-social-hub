"""Zone model for managing 10,000+ music zones across venues"""

from datetime import datetime, timedelta
from typing import Optional
from sqlalchemy import (
    Column, String, Boolean, Integer, Float, ForeignKey, Index, CheckConstraint, text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, validates

from app.models.base import BaseModel


class Zone(BaseModel):
    """
    Zone model representing individual music zones within venues.
    Optimized for 10,000+ zones with real-time status tracking.
    """
    
    __tablename__ = "zones"
    __table_args__ = (
        Index("idx_zone_venue_type", "venue_id", "zone_type"),
        Index("idx_zone_device_status", "soundtrack_device_id", "is_online"),
        Index("idx_zone_last_check", "last_checked_at"),
        Index("idx_zone_venue_online", "venue_id", "is_online"),
        CheckConstraint("volume >= 0 AND volume <= 100", name="check_volume_range"),
        {"comment": "Music zones within venues (lobby, pool, restaurant, etc.)"}
    )
    
    # Relationships
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"), nullable=False, index=True)
    venue = relationship("Venue", back_populates="zones")
    
    # Zone Information
    name = Column(String(100), nullable=False)  # "Main Lobby", "Pool Area"
    zone_type = Column(String(50), nullable=False)  # lobby, restaurant, pool, spa, gym
    floor = Column(String(20))  # "Ground", "1st", "Rooftop"
    capacity = Column(Integer)  # Max occupancy
    
    # Soundtrack Integration
    soundtrack_device_id = Column(String(100), unique=True, index=True)
    soundtrack_zone_id = Column(String(100))
    device_model = Column(String(100))  # Hardware model
    device_serial = Column(String(100))
    
    # Current Status (Real-time)
    is_online = Column(Boolean, default=False, nullable=False, index=True)
    current_playlist_id = Column(String(100))
    current_playlist_name = Column(String(255))
    volume = Column(Integer, default=50)  # 0-100
    is_playing = Column(Boolean, default=False)
    
    # Monitoring
    last_checked_at = Column(DateTime(timezone=True), index=True)
    last_online_at = Column(DateTime(timezone=True))
    last_offline_at = Column(DateTime(timezone=True))
    consecutive_failures = Column(Integer, default=0)
    last_error_message = Column(String(500))
    
    # Performance Metrics (Cached)
    uptime_today = Column(Float)  # Percentage
    uptime_week = Column(Float)  # Percentage
    uptime_month = Column(Float)  # Percentage
    avg_response_time_ms = Column(Integer)  # Milliseconds
    total_outages_month = Column(Integer, default=0)
    total_minutes_offline_month = Column(Integer, default=0)
    
    # Configuration
    default_playlist_id = Column(String(100))
    default_volume = Column(Integer, default=50)
    schedule_enabled = Column(Boolean, default=False)
    schedule = Column(JSONB)  # {"mon": [{"start": "09:00", "end": "22:00", "playlist": "id", "volume": 60}]}
    
    # Volume Automation
    auto_volume_schedule = Column(JSONB)  # Time-based volume adjustments
    occupancy_based_volume = Column(Boolean, default=False)
    weather_based_playlist = Column(Boolean, default=False)
    
    # Alert Settings
    alert_enabled = Column(Boolean, default=True)
    alert_threshold_minutes = Column(Integer)  # Override venue setting
    last_alert_sent_at = Column(DateTime(timezone=True))
    alert_count_today = Column(Integer, default=0)
    
    # Metadata
    metadata = Column(JSONB, default={})
    tags = Column(JSONB, default=[])  # ["high-priority", "customer-facing"]
    
    # Relationships
    monitoring_logs = relationship("MonitoringLog", back_populates="zone", cascade="all, delete-orphan")
    alerts = relationship("Alert", back_populates="zone", cascade="all, delete-orphan")
    
    @validates("zone_type")
    def validate_zone_type(self, key, value):
        """Validate zone type"""
        valid_types = ["lobby", "restaurant", "pool", "spa", "gym", "bar", "retail", "corridor", "outdoor", "other"]
        if value not in valid_types:
            raise ValueError(f"Zone type must be one of: {valid_types}")
        return value
    
    @validates("volume", "default_volume")
    def validate_volume(self, key, value):
        """Ensure volume is within valid range"""
        if value is not None and (value < 0 or value > 100):
            raise ValueError("Volume must be between 0 and 100")
        return value
    
    @property
    def is_critical(self) -> bool:
        """Check if zone is critical (lobby or high-priority)"""
        return self.zone_type == "lobby" or "high-priority" in (self.tags or [])
    
    @property
    def downtime_duration(self) -> Optional[timedelta]:
        """Calculate current downtime duration if offline"""
        if self.is_online or not self.last_offline_at:
            return None
        return datetime.utcnow() - self.last_offline_at
    
    @property
    def requires_alert(self) -> bool:
        """Check if zone requires an alert based on current status"""
        if not self.alert_enabled or self.is_online:
            return False
        
        # Check threshold
        threshold = self.alert_threshold_minutes or self.venue.alert_threshold_minutes or 15
        downtime = self.downtime_duration
        
        if not downtime or downtime.total_seconds() / 60 < threshold:
            return False
        
        # Check cooldown
        if self.last_alert_sent_at:
            cooldown = self.venue.alert_cooldown_minutes or 60
            time_since_last_alert = datetime.utcnow() - self.last_alert_sent_at
            if time_since_last_alert.total_seconds() / 60 < cooldown:
                return False
        
        return True
    
    @property
    def health_status(self) -> str:
        """Get health status category"""
        if self.is_online:
            return "healthy"
        elif self.consecutive_failures > 5:
            return "critical"
        elif self.consecutive_failures > 2:
            return "degraded"
        else:
            return "checking"
    
    def get_current_volume_target(self) -> int:
        """Calculate target volume based on schedule and automation"""
        base_volume = self.volume or self.default_volume or 50
        
        # Check time-based schedule
        if self.auto_volume_schedule:
            current_hour = datetime.now().hour
            for schedule in self.auto_volume_schedule.get("schedules", []):
                if schedule["start_hour"] <= current_hour < schedule["end_hour"]:
                    return schedule["volume"]
        
        return base_volume
    
    def __repr__(self):
        return f"<Zone(id={self.id}, name='{self.name}', venue_id={self.venue_id}, online={self.is_online})>"