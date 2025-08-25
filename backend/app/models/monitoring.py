"""Monitoring and alert models for tracking system health"""

from datetime import datetime
from enum import Enum as PyEnum
from sqlalchemy import (
    Column, String, Boolean, Integer, Float, ForeignKey, Index, Enum, Text
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship

from app.models.base import BaseModel


class AlertSeverity(PyEnum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AlertType(PyEnum):
    """Types of alerts"""
    ZONE_OFFLINE = "zone_offline"
    ZONE_ONLINE = "zone_online"
    VENUE_DEGRADED = "venue_degraded"
    HIGH_RESPONSE_TIME = "high_response_time"
    API_ERROR = "api_error"
    SLA_BREACH = "sla_breach"
    LOW_SATISFACTION = "low_satisfaction"


class MonitoringLog(BaseModel):
    """
    Monitoring log for tracking zone status checks.
    Partitioned by month for efficient storage of millions of records.
    """
    
    __tablename__ = "monitoring_logs"
    __table_args__ = (
        Index("idx_monitoring_zone_time", "zone_id", "created_at"),
        Index("idx_monitoring_status", "status", "created_at"),
        {"comment": "High-volume monitoring logs, partitioned monthly"}
    )
    
    # Relationships
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"), nullable=False)
    zone = relationship("Zone", back_populates="monitoring_logs")
    
    # Status Information
    status = Column(String(20), nullable=False)  # online, offline, error
    is_playing = Column(Boolean)
    current_playlist = Column(String(255))
    volume = Column(Integer)
    
    # Performance Metrics
    response_time_ms = Column(Integer)  # API response time
    check_duration_ms = Column(Integer)  # Total check duration
    
    # Error Information
    error_code = Column(String(50))
    error_message = Column(Text)
    retry_count = Column(Integer, default=0)
    
    # Metadata
    metadata = Column(JSONB, default={})
    
    def __repr__(self):
        return f"<MonitoringLog(id={self.id}, zone_id={self.zone_id}, status={self.status})>"


class Alert(BaseModel):
    """
    Alert model for tracking system alerts and notifications.
    Used for proactive monitoring and issue resolution.
    """
    
    __tablename__ = "alerts"
    __table_args__ = (
        Index("idx_alert_zone_resolved", "zone_id", "resolved"),
        Index("idx_alert_severity_resolved", "severity", "resolved"),
        Index("idx_alert_type_created", "alert_type", "created_at"),
        {"comment": "System alerts for zones and venues"}
    )
    
    # Relationships
    zone_id = Column(UUID(as_uuid=True), ForeignKey("zones.id"))
    zone = relationship("Zone", back_populates="alerts")
    
    venue_id = Column(UUID(as_uuid=True), ForeignKey("venues.id"))
    
    # Alert Details
    alert_type = Column(Enum(AlertType), nullable=False, index=True)
    severity = Column(Enum(AlertSeverity), nullable=False, index=True)
    title = Column(String(255), nullable=False)
    message = Column(Text, nullable=False)
    
    # Resolution
    resolved = Column(Boolean, default=False, nullable=False, index=True)
    resolved_at = Column(DateTime(timezone=True))
    resolved_by = Column(UUID(as_uuid=True))  # Team member ID
    resolution_notes = Column(Text)
    auto_resolved = Column(Boolean, default=False)
    
    # Notifications
    notifications_sent = Column(JSONB, default=[])  # List of sent notifications
    notification_channels = Column(JSONB, default=[])  # ["whatsapp", "email"]
    
    # Escalation
    escalated = Column(Boolean, default=False)
    escalation_level = Column(Integer, default=1)
    escalated_at = Column(DateTime(timezone=True))
    
    # Metadata
    context = Column(JSONB, default={})  # Additional context data
    tags = Column(JSONB, default=[])
    
    @property
    def is_active(self) -> bool:
        """Check if alert is still active"""
        return not self.resolved
    
    @property
    def duration_minutes(self) -> int:
        """Calculate alert duration in minutes"""
        if self.resolved and self.resolved_at:
            delta = self.resolved_at - self.created_at
            return int(delta.total_seconds() / 60)
        elif not self.resolved:
            delta = datetime.utcnow() - self.created_at
            return int(delta.total_seconds() / 60)
        return 0
    
    def __repr__(self):
        return f"<Alert(id={self.id}, type={self.alert_type}, severity={self.severity}, resolved={self.resolved})>"