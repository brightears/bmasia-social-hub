"""Application Configuration"""

from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings
import os
from functools import lru_cache


class Settings(BaseSettings):
    """Application settings with environment variable support"""
    
    # Application
    app_name: str = Field(default="BMA Social", env="APP_NAME")
    app_version: str = Field(default="1.0.0", env="APP_VERSION")
    environment: str = Field(default="development", env="ENVIRONMENT")
    debug: bool = Field(default=False, env="DEBUG")
    log_level: str = Field(default="INFO", env="LOG_LEVEL")
    
    # API Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")
    workers: int = Field(default=4, env="WORKERS")
    
    # Database - Render provides DATABASE_URL automatically
    database_url: str = Field(
        default="postgresql://localhost:5432/bma_social",
        env="DATABASE_URL"
    )
    database_pool_size: int = Field(default=50, env="DATABASE_POOL_SIZE")
    database_max_overflow: int = Field(default=20, env="DATABASE_MAX_OVERFLOW")
    database_pool_timeout: int = Field(default=30, env="DATABASE_POOL_TIMEOUT")
    database_pool_recycle: int = Field(default=3600, env="DATABASE_POOL_RECYCLE")
    
    # Redis
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    redis_max_connections: int = Field(default=100, env="REDIS_MAX_CONNECTIONS")
    redis_decode_responses: bool = Field(default=True, env="REDIS_DECODE_RESPONSES")
    
    # Security
    secret_key: str = Field(default="your-secret-key", env="SECRET_KEY")
    jwt_secret_key: str = Field(default="your-jwt-secret", env="JWT_SECRET_KEY")
    jwt_algorithm: str = Field(default="HS256", env="JWT_ALGORITHM")
    jwt_expiration_hours: int = Field(default=24, env="JWT_EXPIRATION_HOURS")
    cors_origins: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:3001"],
        env="CORS_ORIGINS"
    )
    
    # Soundtrack Your Brand API
    soundtrack_base_url: str = Field(
        default="https://api.soundtrackyourbrand.com/v2",
        env="SOUNDTRACK_BASE_URL"
    )
    soundtrack_client_id: str = Field(default="", env="SOUNDTRACK_CLIENT_ID")
    soundtrack_client_secret: str = Field(default="", env="SOUNDTRACK_CLIENT_SECRET")
    soundtrack_rate_limit: int = Field(default=1000, env="SOUNDTRACK_RATE_LIMIT")
    soundtrack_max_connections: int = Field(default=100, env="SOUNDTRACK_MAX_CONNECTIONS")
    
    # WhatsApp Business API
    whatsapp_api_url: str = Field(
        default="https://graph.facebook.com/v17.0",
        env="WHATSAPP_API_URL"
    )
    whatsapp_access_token: str = Field(default="", env="WHATSAPP_ACCESS_TOKEN")
    whatsapp_verify_token: str = Field(default="", env="WHATSAPP_VERIFY_TOKEN")
    whatsapp_phone_number_id: str = Field(default="", env="WHATSAPP_PHONE_NUMBER_ID")
    whatsapp_webhook_secret: str = Field(default="", env="WHATSAPP_WEBHOOK_SECRET")
    whatsapp_app_secret: str = Field(default="", env="WHATSAPP_APP_SECRET")
    
    # Line Business API
    line_api_url: str = Field(default="https://api.line.me/v2", env="LINE_API_URL")
    line_channel_access_token: str = Field(default="", env="LINE_CHANNEL_ACCESS_TOKEN")
    line_channel_secret: str = Field(default="", env="LINE_CHANNEL_SECRET")
    
    # Google Gemini API
    gemini_api_key: str = Field(default="", env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-2.5-flash", env="GEMINI_MODEL")
    gemini_max_tokens: int = Field(default=8192, env="GEMINI_MAX_TOKENS")
    gemini_temperature: float = Field(default=0.7, env="GEMINI_TEMPERATURE")
    
    # Monitoring
    sentry_dsn: Optional[str] = Field(default=None, env="SENTRY_DSN")
    prometheus_enabled: bool = Field(default=True, env="PROMETHEUS_ENABLED")
    health_check_enabled: bool = Field(default=True, env="HEALTH_CHECK_ENABLED")
    
    # Polling & Monitoring
    polling_interval_seconds: int = Field(default=300, env="POLLING_INTERVAL_SECONDS")
    alert_cooldown_seconds: int = Field(default=3600, env="ALERT_COOLDOWN_SECONDS")
    max_retries: int = Field(default=3, env="MAX_RETRIES")
    batch_size: int = Field(default=100, env="BATCH_SIZE")
    
    # Rate Limiting
    rate_limit_enabled: bool = Field(default=True, env="RATE_LIMIT_ENABLED")
    rate_limit_per_minute: int = Field(default=60, env="RATE_LIMIT_PER_MINUTE")
    rate_limit_per_hour: int = Field(default=1000, env="RATE_LIMIT_PER_HOUR")
    
    # Email Configuration
    smtp_host: Optional[str] = Field(default=None, env="SMTP_HOST")
    smtp_port: Optional[int] = Field(default=587, env="SMTP_PORT")
    smtp_user: Optional[str] = Field(default=None, env="SMTP_USER")
    smtp_password: Optional[str] = Field(default=None, env="SMTP_PASSWORD")
    smtp_from_email: Optional[str] = Field(default="noreply@bma-social.com", env="SMTP_FROM_EMAIL")
    
    # OpenWeatherMap API
    openweathermap_api_key: Optional[str] = Field(default=None, env="OPENWEATHERMAP_API_KEY")
    
    # Celery Configuration
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(default="redis://localhost:6379/2", env="CELERY_RESULT_BACKEND")
    celery_task_always_eager: bool = Field(default=False, env="CELERY_TASK_ALWAYS_EAGER")
    celery_task_eager_propagates: bool = Field(default=False, env="CELERY_TASK_EAGER_PROPAGATES")
    
    @field_validator("cors_origins", mode='before')
    @classmethod
    def parse_cors_origins(cls, v):
        if isinstance(v, str):
            return [origin.strip() for origin in v.split(",")]
        return v
    
    @field_validator("environment")
    @classmethod
    def validate_environment(cls, v):
        allowed = {"development", "staging", "production", "testing"}
        if v not in allowed:
            raise ValueError(f"Environment must be one of: {allowed}")
        return v
    
    @property
    def is_production(self) -> bool:
        return self.environment == "production"
    
    @property
    def is_development(self) -> bool:
        return self.environment == "development"
    
    @property
    def is_testing(self) -> bool:
        return self.environment == "testing"
    
    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False
    }


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()


# Create a global settings instance
settings = get_settings()