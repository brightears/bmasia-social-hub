"""
Alembic environment configuration with async support for BMA Social.
Handles database migrations for production deployment on Render.
"""

import asyncio
import os
import sys
from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy import engine_from_config
from alembic import context

# Add parent directory to path to import app modules
sys.path.append(str(Path(__file__).parent.parent))

from app.config import settings
from app.core.database import Base

# Import all models to ensure they're registered with Base
from app.models import (
    Venue,
    Zone,
    Conversation,
    Message,
    SatisfactionScore,
    MonitoringLog,
    Alert,
    Campaign,
    CampaignRecipient,
    TeamMember,
)

# Alembic Config object
config = context.config

# Interpret the config file for logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Set target metadata for autogenerate
target_metadata = Base.metadata

# Get database URL from environment or settings
def get_database_url():
    """Get database URL from environment or settings"""
    # Use DATABASE_URL from environment (Render provides this)
    db_url = os.getenv("DATABASE_URL")
    
    if db_url:
        # Convert async URLs to sync URLs for standard SQLAlchemy
        if db_url.startswith("postgresql+asyncpg://"):
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://", 1)
        elif db_url.startswith("asyncpg://"):
            db_url = db_url.replace("asyncpg://", "postgresql://", 1)
        elif db_url.startswith("postgres://"):
            db_url = db_url.replace("postgres://", "postgresql://", 1)
    else:
        # Fallback to settings
        db_url = settings.database_url
        # Also convert from async to sync
        if "postgresql+asyncpg://" in db_url:
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
        elif "asyncpg://" in db_url:
            db_url = db_url.replace("asyncpg://", "postgresql://")
    
    return db_url


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.
    
    This configures the context with just a URL
    and not an Engine, though an Engine is acceptable
    here as well. By skipping the Engine creation
    we don't even need a DBAPI to be available.
    
    Calls to context.execute() here emit the given string to the
    script output.
    """
    url = get_database_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
        compare_server_default=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run migrations with the provided connection"""
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
        compare_type=True,
        compare_server_default=True,
        include_schemas=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_sync_migrations() -> None:
    """
    Run migrations in 'online' mode with synchronous connection.
    
    In this scenario we need to create an Engine
    and associate a connection with the context.
    """
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = get_database_url()
    
    # Configure connection pool for production
    if settings.is_production:
        configuration["poolclass"] = "NullPool"
    else:
        configuration["poolclass"] = "StaticPool"
    
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool if settings.is_production else pool.StaticPool,
    )

    with connectable.connect() as connection:
        do_run_migrations(connection)

    connectable.dispose()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode"""
    run_sync_migrations()


# Determine which mode to run in
if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()