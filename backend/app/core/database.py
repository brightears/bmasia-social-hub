"""
Database connection and session management with optimizations for scale.
Designed for 10,000+ zones and 120,000+ API calls/hour.
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from enum import Enum
from typing import Any, AsyncGenerator, Dict, Optional, List
from datetime import datetime, timedelta
import random

from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import declarative_base, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool
from sqlalchemy.exc import OperationalError, DBAPIError
import asyncpg

from app.config import settings

logger = logging.getLogger(__name__)

# Base model for all database models
Base = declarative_base()


class DatabaseRole(Enum):
    """Database connection roles for read/write splitting"""
    PRIMARY = "primary"
    REPLICA = "replica"
    ANALYTICS = "analytics"


class ConnectionRetryPolicy:
    """Retry policy for database connections"""
    def __init__(
        self,
        max_retries: int = 3,
        initial_delay: float = 0.1,
        max_delay: float = 5.0,
        exponential_base: float = 2.0,
        jitter: bool = True
    ):
        self.max_retries = max_retries
        self.initial_delay = initial_delay
        self.max_delay = max_delay
        self.exponential_base = exponential_base
        self.jitter = jitter
    
    def get_delay(self, attempt: int) -> float:
        """Calculate delay with exponential backoff and optional jitter"""
        delay = min(
            self.initial_delay * (self.exponential_base ** attempt),
            self.max_delay
        )
        
        if self.jitter:
            delay *= (0.5 + random.random())
        
        return delay


class DatabaseManager:
    """
    Manages database connections with optimizations for high-volume operations.
    Supports connection pooling, read/write splitting, and performance monitoring.
    """
    
    def __init__(self):
        self.engines: Dict[DatabaseRole, Optional[AsyncEngine]] = {
            DatabaseRole.PRIMARY: None,
            DatabaseRole.REPLICA: None,
            DatabaseRole.ANALYTICS: None,
        }
        self.session_makers: Dict[DatabaseRole, Optional[async_sessionmaker]] = {
            DatabaseRole.PRIMARY: None,
            DatabaseRole.REPLICA: None,
            DatabaseRole.ANALYTICS: None,
        }
        self.retry_policy = ConnectionRetryPolicy()
        self._performance_metrics = {
            "queries_executed": 0,
            "queries_failed": 0,
            "slow_queries": [],
            "connection_errors": 0,
            "last_health_check": None,
        }
    
    async def initialize(self):
        """Initialize database connections with proper pooling for Render deployment"""
        
        # Primary database configuration (writes)
        primary_config = {
            "pool_size": settings.database_pool_size,
            "max_overflow": settings.database_max_overflow,
            "pool_timeout": settings.database_pool_timeout,
            "pool_recycle": settings.database_pool_recycle,
            "pool_pre_ping": True,
            "echo": settings.debug and settings.environment != "production",
            "echo_pool": settings.debug and settings.environment != "production",
            "connect_args": {
                "server_settings": {
                    "application_name": f"bma_social_{settings.environment}",
                    "jit": "off",
                },
                "command_timeout": 60,
                "prepared_statement_cache_size": 0,  # For pgbouncer compatibility
                "ssl": "require" if settings.is_production else "prefer",
            },
        }
        
        # Create primary engine
        self.engines[DatabaseRole.PRIMARY] = create_async_engine(
            self._get_database_url(DatabaseRole.PRIMARY),
            **primary_config
        )
        
        # Create replica engine if URL is available (future scaling)
        replica_url = self._get_database_url(DatabaseRole.REPLICA)
        if replica_url:
            replica_config = primary_config.copy()
            replica_config["pool_size"] = settings.database_pool_size * 2  # More connections for reads
            self.engines[DatabaseRole.REPLICA] = create_async_engine(
                replica_url,
                **replica_config
            )
        
        # Create session makers
        for role, engine in self.engines.items():
            if engine:
                self.session_makers[role] = async_sessionmaker(
                    engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                    autoflush=False,
                    autocommit=False,
                )
        
        # Verify connections
        await self._verify_connections()
        
        logger.info(f"Database initialized for environment: {settings.environment}")
    
    def _get_database_url(self, role: DatabaseRole) -> Optional[str]:
        """Get database URL based on role"""
        # For now, all roles use the same URL
        # In production, you can add read replicas via environment variables
        if role == DatabaseRole.PRIMARY:
            return settings.database_url
        elif role == DatabaseRole.REPLICA:
            # Check for replica URL in environment
            return getattr(settings, "database_replica_url", None)
        elif role == DatabaseRole.ANALYTICS:
            # Check for analytics DB URL
            return getattr(settings, "database_analytics_url", None)
        return None
    
    async def _verify_connections(self):
        """Verify all database connections are working"""
        for role, engine in self.engines.items():
            if engine:
                try:
                    async with engine.connect() as conn:
                        result = await conn.execute(text("SELECT 1"))
                        await conn.commit()
                    logger.info(f"Database connection verified for role: {role.value}")
                except Exception as e:
                    logger.error(f"Failed to verify connection for role {role.value}: {e}")
                    if role == DatabaseRole.PRIMARY:
                        raise  # Primary connection is critical
    
    async def get_session(
        self,
        role: DatabaseRole = DatabaseRole.PRIMARY
    ) -> AsyncGenerator[AsyncSession, None]:
        """
        Get a database session with automatic retry logic.
        
        Args:
            role: Database role (PRIMARY for writes, REPLICA for reads)
        
        Yields:
            AsyncSession: Database session
        """
        session_maker = self.session_makers.get(role)
        
        # Fallback to primary if requested role not available
        if not session_maker:
            session_maker = self.session_makers[DatabaseRole.PRIMARY]
        
        if not session_maker:
            raise RuntimeError("Database not initialized")
        
        attempt = 0
        last_error = None
        
        while attempt < self.retry_policy.max_retries:
            try:
                async with session_maker() as session:
                    yield session
                    await session.commit()
                    return
            except (OperationalError, DBAPIError) as e:
                last_error = e
                attempt += 1
                self._performance_metrics["connection_errors"] += 1
                
                if attempt < self.retry_policy.max_retries:
                    delay = self.retry_policy.get_delay(attempt)
                    logger.warning(
                        f"Database connection error (attempt {attempt}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(f"Max retries reached for database connection: {e}")
                    raise
            except Exception as e:
                await session.rollback()
                raise
    
    @asynccontextmanager
    async def transaction(
        self,
        isolation_level: Optional[str] = None,
        read_only: bool = False
    ):
        """
        Create a database transaction with optional isolation level.
        
        Args:
            isolation_level: SQL isolation level (SERIALIZABLE, REPEATABLE READ, etc.)
            read_only: Whether this is a read-only transaction
        """
        role = DatabaseRole.REPLICA if read_only else DatabaseRole.PRIMARY
        
        async with self.get_session(role) as session:
            if isolation_level:
                await session.execute(
                    text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
                )
            
            if read_only:
                await session.execute(text("SET TRANSACTION READ ONLY"))
            
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
    
    async def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        role: DatabaseRole = DatabaseRole.PRIMARY
    ) -> Any:
        """Execute a raw SQL query with performance tracking"""
        start_time = time.time()
        
        try:
            async with self.get_session(role) as session:
                result = await session.execute(text(query), params or {})
                await session.commit()
                
                self._performance_metrics["queries_executed"] += 1
                
                # Track slow queries
                execution_time = time.time() - start_time
                if execution_time > 1.0:  # Log queries slower than 1 second
                    self._performance_metrics["slow_queries"].append({
                        "query": query[:100],  # First 100 chars
                        "execution_time": execution_time,
                        "timestamp": datetime.utcnow().isoformat()
                    })
                    
                    # Keep only last 100 slow queries
                    if len(self._performance_metrics["slow_queries"]) > 100:
                        self._performance_metrics["slow_queries"] = \
                            self._performance_metrics["slow_queries"][-100:]
                
                return result
        except Exception as e:
            self._performance_metrics["queries_failed"] += 1
            logger.error(f"Query execution failed: {e}")
            raise
    
    async def bulk_insert(
        self,
        table_name: str,
        records: List[Dict[str, Any]],
        batch_size: int = 1000
    ):
        """
        Perform bulk insert with batching for optimal performance.
        
        Args:
            table_name: Name of the table to insert into
            records: List of dictionaries representing records
            batch_size: Number of records to insert per batch
        """
        if not records:
            return
        
        async with self.get_session() as session:
            # Process in batches to avoid memory issues
            for i in range(0, len(records), batch_size):
                batch = records[i:i + batch_size]
                
                # Build insert statement
                columns = list(batch[0].keys())
                placeholders = ", ".join([f":{col}" for col in columns])
                insert_query = f"""
                    INSERT INTO {table_name} ({', '.join(columns)})
                    VALUES ({placeholders})
                    ON CONFLICT DO NOTHING
                """
                
                # Execute batch insert
                await session.execute(text(insert_query), batch)
            
            await session.commit()
            logger.info(f"Bulk inserted {len(records)} records into {table_name}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Perform database health check and return metrics"""
        health_status = {
            "status": "healthy",
            "timestamp": datetime.utcnow().isoformat(),
            "connections": {},
            "performance_metrics": self._performance_metrics.copy(),
        }
        
        # Check each connection
        for role, engine in self.engines.items():
            if engine:
                try:
                    async with engine.connect() as conn:
                        start = time.time()
                        await conn.execute(text("SELECT 1"))
                        latency = (time.time() - start) * 1000  # ms
                        
                        # Get pool stats
                        pool_stats = {
                            "size": engine.pool.size(),
                            "checked_in": engine.pool.checkedin(),
                            "overflow": engine.pool.overflow(),
                            "latency_ms": round(latency, 2),
                        }
                        
                        health_status["connections"][role.value] = {
                            "status": "connected",
                            "pool_stats": pool_stats,
                        }
                except Exception as e:
                    health_status["status"] = "degraded"
                    health_status["connections"][role.value] = {
                        "status": "error",
                        "error": str(e),
                    }
        
        self._performance_metrics["last_health_check"] = datetime.utcnow().isoformat()
        return health_status
    
    async def close(self):
        """Close all database connections"""
        for role, engine in self.engines.items():
            if engine:
                await engine.dispose()
                logger.info(f"Closed database connection for role: {role.value}")


# Create global database manager instance
db_manager = DatabaseManager()


# FastAPI dependency functions
async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Get primary database session for FastAPI dependency injection"""
    async with db_manager.get_session(DatabaseRole.PRIMARY) as session:
        yield session


async def get_read_db() -> AsyncGenerator[AsyncSession, None]:
    """Get read-only database session for FastAPI dependency injection"""
    role = DatabaseRole.REPLICA if db_manager.engines[DatabaseRole.REPLICA] else DatabaseRole.PRIMARY
    async with db_manager.get_session(role) as session:
        yield session


async def get_analytics_db() -> AsyncGenerator[AsyncSession, None]:
    """Get analytics database session for FastAPI dependency injection"""
    role = DatabaseRole.ANALYTICS if db_manager.engines[DatabaseRole.ANALYTICS] else DatabaseRole.PRIMARY
    async with db_manager.get_session(role) as session:
        yield session


# Performance tracking decorator
def track_query_performance(operation_name: str):
    """Decorator to track query performance metrics"""
    def decorator(func):
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = await func(*args, **kwargs)
                execution_time = time.time() - start_time
                
                # Log slow operations
                if execution_time > 1.0:
                    logger.warning(
                        f"Slow operation '{operation_name}': {execution_time:.2f}s"
                    )
                
                return result
            except Exception as e:
                logger.error(f"Operation '{operation_name}' failed: {e}")
                raise
        
        return wrapper
    return decorator