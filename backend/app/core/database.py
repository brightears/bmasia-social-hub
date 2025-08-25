"""
Database connection and session management with optimizations for scale.
Designed for 10,000+ zones and 120,000+ API calls/hour.
Using psycopg2 with optimized connection pooling for Render deployment.
"""

import logging
import time
from contextlib import contextmanager
from enum import Enum
from typing import Any, Generator, Dict, Optional, List
from datetime import datetime, timedelta
import random
import threading

from sqlalchemy import create_engine, event, pool, text
from sqlalchemy.orm import declarative_base, sessionmaker, Session, scoped_session
from sqlalchemy.pool import QueuePool, NullPool, StaticPool
from sqlalchemy.exc import OperationalError, DBAPIError
import psycopg2
from psycopg2 import pool as pg_pool
from psycopg2.extras import RealDictCursor, execute_batch

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
    Uses psycopg2 with SQLAlchemy for optimal performance on Render.
    """
    
    def __init__(self):
        self.engines: Dict[DatabaseRole, Optional[Any]] = {
            DatabaseRole.PRIMARY: None,
            DatabaseRole.REPLICA: None,
            DatabaseRole.ANALYTICS: None,
        }
        self.session_makers: Dict[DatabaseRole, Optional[scoped_session]] = {
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
        self._lock = threading.Lock()
    
    def initialize(self):
        """Initialize database connections with proper pooling for Render deployment"""
        
        # Primary database configuration optimized for BMA Social scale
        # Using QueuePool for better connection management with high concurrency
        primary_config = {
            "poolclass": QueuePool,
            "pool_size": settings.database_pool_size,  # Base number of connections
            "max_overflow": settings.database_max_overflow,  # Additional connections when needed
            "pool_timeout": settings.database_pool_timeout,  # Timeout waiting for connection
            "pool_recycle": settings.database_pool_recycle,  # Recycle connections after this time
            "pool_pre_ping": True,  # Test connections before using
            "echo": settings.debug and settings.environment != "production",
            "echo_pool": settings.debug and settings.environment != "production",
            "connect_args": {
                "connect_timeout": 10,
                "application_name": f"bma_social_{settings.environment}",
                "options": "-c statement_timeout=60000 -c lock_timeout=10000",  # 60s statement, 10s lock timeout
                "keepalives": 1,
                "keepalives_idle": 30,
                "keepalives_interval": 10,
                "keepalives_count": 5,
                "sslmode": "require" if settings.is_production else "prefer",
            },
            "execution_options": {
                "isolation_level": "READ_COMMITTED",  # Default isolation level
                "postgresql_readonly": False,
                "postgresql_deferrable": False,
            },
        }
        
        # Create primary engine with psycopg2
        db_url = self._get_database_url(DatabaseRole.PRIMARY)
        if db_url:
            # Convert async URL format to sync format if needed
            db_url = db_url.replace("postgresql+asyncpg://", "postgresql://")
            db_url = db_url.replace("asyncpg://", "postgresql://")
            
            self.engines[DatabaseRole.PRIMARY] = create_engine(
                db_url,
                **primary_config
            )
        
        # Create replica engine if URL is available (future scaling)
        replica_url = self._get_database_url(DatabaseRole.REPLICA)
        if replica_url:
            replica_url = replica_url.replace("postgresql+asyncpg://", "postgresql://")
            replica_url = replica_url.replace("asyncpg://", "postgresql://")
            
            replica_config = primary_config.copy()
            replica_config["pool_size"] = settings.database_pool_size * 2  # More connections for reads
            replica_config["connect_args"]["application_name"] = f"bma_social_{settings.environment}_read"
            self.engines[DatabaseRole.REPLICA] = create_engine(
                replica_url,
                **replica_config
            )
        
        # Create scoped session makers for thread safety
        for role, engine in self.engines.items():
            if engine:
                session_factory = sessionmaker(
                    bind=engine,
                    expire_on_commit=False,
                    autoflush=False,
                    autocommit=False,
                )
                # Use scoped_session for thread-local sessions
                self.session_makers[role] = scoped_session(session_factory)
        
        # Set up connection pool logging and optimization
        self._setup_pool_listeners()
        
        # Verify connections
        self._verify_connections()
        
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
    
    def _setup_pool_listeners(self):
        """Set up connection pool event listeners for monitoring and optimization"""
        for role, engine in self.engines.items():
            if engine:
                # Log connection checkout/checkin for monitoring
                @event.listens_for(engine, "connect")
                def receive_connect(dbapi_conn, connection_record):
                    # Set performance-related parameters on each new connection
                    with dbapi_conn.cursor() as cursor:
                        # Optimize for BMA Social's workload
                        cursor.execute("SET work_mem = '32MB'")
                        cursor.execute("SET effective_cache_size = '4GB'")
                        cursor.execute("SET random_page_cost = 1.1")  # For SSD storage
                        cursor.execute("SET effective_io_concurrency = 200")  # For SSD
                        cursor.execute("SET max_parallel_workers_per_gather = 2")
                        cursor.execute("SET max_parallel_workers = 8")
                        
                        # Set application name for monitoring
                        app_name = f"bma_{role.value}_{settings.environment}"
                        cursor.execute(f"SET application_name = '{app_name}'")
                
                @event.listens_for(engine, "checkout")
                def receive_checkout(dbapi_conn, connection_record, connection_proxy):
                    # Track connection age for recycling
                    connection_record.info['checkout_time'] = time.time()
                
                @event.listens_for(engine, "checkin")
                def receive_checkin(dbapi_conn, connection_record):
                    # Log long-held connections
                    if 'checkout_time' in connection_record.info:
                        duration = time.time() - connection_record.info['checkout_time']
                        if duration > 5.0:  # Connections held longer than 5 seconds
                            logger.warning(f"Long connection hold time: {duration:.2f}s for {role.value}")
    
    def _verify_connections(self):
        """Verify all database connections are working"""
        for role, engine in self.engines.items():
            if engine:
                try:
                    with engine.connect() as conn:
                        result = conn.execute(text("SELECT 1"))
                        conn.commit()
                    logger.info(f"Database connection verified for role: {role.value}")
                except Exception as e:
                    logger.error(f"Failed to verify connection for role {role.value}: {e}")
                    if role == DatabaseRole.PRIMARY:
                        raise  # Primary connection is critical
    
    @contextmanager
    def get_session(
        self,
        role: DatabaseRole = DatabaseRole.PRIMARY
    ) -> Generator[Session, None, None]:
        """
        Get a database session with automatic retry logic.
        
        Args:
            role: Database role (PRIMARY for writes, REPLICA for reads)
        
        Yields:
            Session: Database session
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
            session = None
            try:
                session = session_maker()
                yield session
                session.commit()
                return
            except (OperationalError, DBAPIError) as e:
                if session:
                    session.rollback()
                last_error = e
                attempt += 1
                self._performance_metrics["connection_errors"] += 1
                
                if attempt < self.retry_policy.max_retries:
                    delay = self.retry_policy.get_delay(attempt)
                    logger.warning(
                        f"Database connection error (attempt {attempt}), "
                        f"retrying in {delay:.2f}s: {e}"
                    )
                    time.sleep(delay)
                else:
                    logger.error(f"Max retries reached for database connection: {e}")
                    raise
            except Exception as e:
                if session:
                    session.rollback()
                raise
            finally:
                if session:
                    session.close()
    
    @contextmanager
    def transaction(
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
        
        with self.get_session(role) as session:
            if isolation_level:
                session.execute(
                    text(f"SET TRANSACTION ISOLATION LEVEL {isolation_level}")
                )
            
            if read_only:
                session.execute(text("SET TRANSACTION READ ONLY"))
            
            try:
                yield session
                session.commit()
            except Exception:
                session.rollback()
                raise
    
    def execute_query(
        self,
        query: str,
        params: Optional[Dict[str, Any]] = None,
        role: DatabaseRole = DatabaseRole.PRIMARY
    ) -> Any:
        """Execute a raw SQL query with performance tracking"""
        start_time = time.time()
        
        try:
            with self.get_session(role) as session:
                result = session.execute(text(query), params or {})
                session.commit()
                
                with self._lock:
                    self._performance_metrics["queries_executed"] += 1
                
                # Track slow queries
                execution_time = time.time() - start_time
                if execution_time > 1.0:  # Log queries slower than 1 second
                    with self._lock:
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
            with self._lock:
                self._performance_metrics["queries_failed"] += 1
            logger.error(f"Query execution failed: {e}")
            raise
    
    def bulk_insert(
        self,
        table_name: str,
        records: List[Dict[str, Any]],
        batch_size: int = 1000
    ):
        """
        Perform bulk insert with batching for optimal performance.
        Uses psycopg2's execute_batch for maximum efficiency.
        
        Args:
            table_name: Name of the table to insert into
            records: List of dictionaries representing records
            batch_size: Number of records to insert per batch
        """
        if not records:
            return
        
        with self.get_session() as session:
            # Get raw psycopg2 connection for bulk operations
            raw_conn = session.connection().connection
            
            with raw_conn.cursor() as cursor:
                # Process in batches to avoid memory issues
                for i in range(0, len(records), batch_size):
                    batch = records[i:i + batch_size]
                    
                    # Build insert statement
                    columns = list(batch[0].keys())
                    placeholders = ', '.join(['%s'] * len(columns))
                    insert_query = f"""
                        INSERT INTO {table_name} ({', '.join(columns)})
                        VALUES ({placeholders})
                        ON CONFLICT DO NOTHING
                    """
                    
                    # Convert dict records to tuples for execute_batch
                    values = [tuple(record[col] for col in columns) for record in batch]
                    
                    # Use execute_batch for optimal performance
                    execute_batch(
                        cursor,
                        insert_query,
                        values,
                        page_size=min(100, batch_size)  # Optimize page size
                    )
            
            session.commit()
            logger.info(f"Bulk inserted {len(records)} records into {table_name}")
    
    def health_check(self) -> Dict[str, Any]:
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
                    with engine.connect() as conn:
                        start = time.time()
                        conn.execute(text("SELECT 1"))
                        latency = (time.time() - start) * 1000  # ms
                        
                        # Get pool stats
                        pool = engine.pool
                        pool_stats = {
                            "size": pool.size(),
                            "checked_in": pool.checkedin(),
                            "overflow": pool.overflow(),
                            "total": pool.size() + pool.overflow(),
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
        
        with self._lock:
            self._performance_metrics["last_health_check"] = datetime.utcnow().isoformat()
        
        return health_status
    
    def close(self):
        """Close all database connections"""
        for role, engine in self.engines.items():
            if engine:
                engine.dispose()
                logger.info(f"Closed database connection for role: {role.value}")
        
        # Remove scoped sessions
        for role, session_maker in self.session_makers.items():
            if session_maker:
                session_maker.remove()


# Create global database manager instance
db_manager = DatabaseManager()


# FastAPI dependency functions
def get_db() -> Generator[Session, None, None]:
    """Get primary database session for FastAPI dependency injection"""
    with db_manager.get_session(DatabaseRole.PRIMARY) as session:
        yield session


def get_read_db() -> Generator[Session, None, None]:
    """Get read-only database session for FastAPI dependency injection"""
    role = DatabaseRole.REPLICA if db_manager.engines[DatabaseRole.REPLICA] else DatabaseRole.PRIMARY
    with db_manager.get_session(role) as session:
        yield session


def get_analytics_db() -> Generator[Session, None, None]:
    """Get analytics database session for FastAPI dependency injection"""
    role = DatabaseRole.ANALYTICS if db_manager.engines[DatabaseRole.ANALYTICS] else DatabaseRole.PRIMARY
    with db_manager.get_session(role) as session:
        yield session


# Performance tracking decorator
def track_query_performance(operation_name: str):
    """Decorator to track query performance metrics"""
    def decorator(func):
        def wrapper(*args, **kwargs):
            start_time = time.time()
            try:
                result = func(*args, **kwargs)
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


# Utility function for high-performance batch operations
def execute_batch_optimized(
    session: Session,
    query: str,
    data: List[tuple],
    page_size: int = 100
) -> None:
    """
    Execute batch operations with optimal performance using psycopg2's execute_batch.
    
    Args:
        session: SQLAlchemy session
        query: SQL query with placeholders
        data: List of tuples containing values
        page_size: Number of records per batch page
    """
    raw_conn = session.connection().connection
    with raw_conn.cursor() as cursor:
        execute_batch(cursor, query, data, page_size=page_size)


# Connection pool monitoring function
def get_pool_stats() -> Dict[str, Any]:
    """Get current connection pool statistics for monitoring"""
    stats = {}
    for role, engine in db_manager.engines.items():
        if engine and engine.pool:
            pool = engine.pool
            stats[role.value] = {
                "size": pool.size(),
                "checked_in": pool.checkedin(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
                "total": pool.size() + pool.overflow(),
            }
    return stats