"""Data models for Soundtrack Your Brand API integration"""

from typing import Optional, List, Dict, Any, Union
from datetime import datetime
from enum import Enum
from pydantic import BaseModel, Field, validator


class ZoneState(str, Enum):
    """Zone playback states"""
    PLAYING = "playing"
    PAUSED = "paused"
    STOPPED = "stopped"
    OFFLINE = "offline"
    UNKNOWN = "unknown"


class OperationType(str, Enum):
    """Bulk operation types"""
    STATUS_CHECK = "status_check"
    VOLUME_CHANGE = "volume_change"
    PLAYLIST_CHANGE = "playlist_change"
    PLAYBACK_CONTROL = "playback_control"
    DEVICE_RESTART = "device_restart"


class APIResponse(BaseModel):
    """Generic API response wrapper"""
    success: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    status_code: int = 200
    response_time_ms: Optional[int] = None
    cached: bool = False
    retry_count: int = 0
    
    class Config:
        use_enum_values = True


class DeviceInfo(BaseModel):
    """Device information model"""
    device_id: str
    zone_id: str
    model: str
    serial_number: Optional[str] = None
    firmware_version: Optional[str] = None
    ip_address: Optional[str] = None
    mac_address: Optional[str] = None
    last_seen: Optional[datetime] = None
    online: bool = False
    signal_strength: Optional[int] = Field(None, ge=-100, le=0)  # dBm
    cpu_usage: Optional[float] = Field(None, ge=0, le=100)
    memory_usage: Optional[float] = Field(None, ge=0, le=100)
    temperature: Optional[float] = None  # Celsius
    uptime_seconds: Optional[int] = None
    
    @validator('signal_strength')
    def validate_signal_strength(cls, v):
        if v is not None and not -100 <= v <= 0:
            raise ValueError("Signal strength must be between -100 and 0 dBm")
        return v


class PlaylistInfo(BaseModel):
    """Playlist information model"""
    playlist_id: str
    name: str
    description: Optional[str] = None
    duration_seconds: Optional[int] = None
    track_count: Optional[int] = None
    genre: Optional[str] = None
    energy_level: Optional[str] = None  # low, medium, high
    explicit_content: bool = False
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    is_scheduled: bool = False
    schedule: Optional[Dict[str, Any]] = None  # Day/time schedule
    tags: List[str] = Field(default_factory=list)


class VolumeControl(BaseModel):
    """Volume control model"""
    zone_id: str
    current_volume: int = Field(ge=0, le=100)
    target_volume: int = Field(ge=0, le=100)
    fade_duration_ms: Optional[int] = Field(None, ge=0, le=10000)
    scheduled: bool = False
    schedule_time: Optional[datetime] = None
    
    @validator('current_volume', 'target_volume')
    def validate_volume(cls, v):
        if not 0 <= v <= 100:
            raise ValueError("Volume must be between 0 and 100")
        return v


class ZoneStatus(BaseModel):
    """Comprehensive zone status model"""
    zone_id: str
    device_id: str
    name: str
    state: ZoneState = ZoneState.UNKNOWN
    online: bool = False
    volume: int = Field(50, ge=0, le=100)
    is_playing: bool = False
    
    # Current playback
    current_playlist: Optional[PlaylistInfo] = None
    current_track: Optional[str] = None
    current_track_artist: Optional[str] = None
    current_track_duration_ms: Optional[int] = None
    current_track_progress_ms: Optional[int] = None
    
    # Device details
    device_info: Optional[DeviceInfo] = None
    
    # Performance metrics
    response_time_ms: Optional[int] = None
    last_checked_at: Optional[datetime] = None
    consecutive_failures: int = 0
    last_error: Optional[str] = None
    
    # Health indicators
    health_score: Optional[float] = Field(None, ge=0, le=100)
    uptime_percentage: Optional[float] = Field(None, ge=0, le=100)
    
    @property
    def is_healthy(self) -> bool:
        """Check if zone is in healthy state"""
        return self.online and self.consecutive_failures == 0
    
    @property
    def needs_attention(self) -> bool:
        """Check if zone needs attention"""
        return not self.online or self.consecutive_failures > 3
    
    def calculate_health_score(self) -> float:
        """Calculate zone health score (0-100)"""
        score = 100.0
        
        if not self.online:
            score -= 50
        
        score -= min(self.consecutive_failures * 10, 30)
        
        if self.response_time_ms:
            if self.response_time_ms > 5000:
                score -= 20
            elif self.response_time_ms > 2000:
                score -= 10
        
        if self.device_info:
            if self.device_info.cpu_usage and self.device_info.cpu_usage > 90:
                score -= 10
            if self.device_info.memory_usage and self.device_info.memory_usage > 90:
                score -= 10
            if self.device_info.signal_strength and self.device_info.signal_strength < -70:
                score -= 10
        
        return max(score, 0)


class BulkOperationRequest(BaseModel):
    """Request for bulk operations"""
    operation_type: OperationType
    zone_ids: List[str]
    parameters: Optional[Dict[str, Any]] = None
    priority: int = Field(5, ge=1, le=10)  # 1=lowest, 10=highest
    batch_size: int = Field(100, ge=1, le=500)
    parallel_requests: int = Field(10, ge=1, le=50)
    timeout_seconds: int = Field(30, ge=5, le=300)
    retry_failed: bool = True
    max_retries: int = Field(3, ge=0, le=5)


class BulkOperationResult(BaseModel):
    """Result of bulk operations"""
    operation_id: str
    operation_type: OperationType
    total_zones: int
    successful: int = 0
    failed: int = 0
    skipped: int = 0
    
    results: List[APIResponse] = Field(default_factory=list)
    failed_zones: List[Dict[str, str]] = Field(default_factory=list)  # zone_id: error
    
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: Optional[float] = None
    
    average_response_time_ms: Optional[float] = None
    cache_hit_rate: Optional[float] = None
    retry_count: int = 0
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate percentage"""
        if self.total_zones == 0:
            return 0.0
        return (self.successful / self.total_zones) * 100
    
    @property
    def is_complete(self) -> bool:
        """Check if operation is complete"""
        return self.end_time is not None
    
    def add_result(self, zone_id: str, response: APIResponse):
        """Add a result for a zone"""
        self.results.append(response)
        if response.success:
            self.successful += 1
        else:
            self.failed += 1
            self.failed_zones.append({zone_id: response.error or "Unknown error"})


class RateLimitInfo(BaseModel):
    """Rate limit tracking information"""
    limit: int
    remaining: int
    reset_at: datetime
    window_seconds: int = 60
    
    @property
    def is_exceeded(self) -> bool:
        """Check if rate limit is exceeded"""
        return self.remaining <= 0
    
    @property
    def usage_percentage(self) -> float:
        """Calculate usage percentage"""
        if self.limit == 0:
            return 0.0
        return ((self.limit - self.remaining) / self.limit) * 100
    
    @property
    def seconds_until_reset(self) -> int:
        """Calculate seconds until rate limit reset"""
        now = datetime.utcnow()
        if self.reset_at > now:
            return int((self.reset_at - now).total_seconds())
        return 0


class CircuitBreakerState(str, Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreakerInfo(BaseModel):
    """Circuit breaker status information"""
    state: CircuitBreakerState
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: Optional[datetime] = None
    last_success_time: Optional[datetime] = None
    next_attempt_time: Optional[datetime] = None
    error_percentage: float = 0.0
    
    @property
    def is_available(self) -> bool:
        """Check if circuit breaker allows requests"""
        return self.state != CircuitBreakerState.OPEN