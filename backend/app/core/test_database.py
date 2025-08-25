"""
Test suite for the production-ready database module
Demonstrates usage patterns and validates functionality

NOTE: This file needs to be updated to work with the new synchronous database setup.
Many async functions and method calls need to be converted to synchronous.
"""

import asyncio
import time
from datetime import datetime
from typing import List

import pytest
from sqlalchemy import Column, DateTime, Integer, String, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Session

from .database import (
    Base,
    DatabaseRole,
    db_manager,
    get_analytics_db,
    get_db,
    get_read_db,
    track_query_performance,
)


# Example model for testing
class Venue(Base):
    __tablename__ = "venues"
    
    id = Column(Integer, primary_key=True)
    external_id = Column(String(100), unique=True, index=True)
    name = Column(String(255), nullable=False)
    configuration = Column(JSONB, default={})
    status = Column(String(50), index=True)
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())


class MonitoringLog(Base):
    __tablename__ = "monitoring_logs"
    
    id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, index=True)
    event_type = Column(String(50), index=True)
    event_data = Column(JSONB)
    created_at = Column(DateTime, server_default=func.now(), index=True)


# Example usage patterns
class VenueRepository:
    """Repository pattern for venue operations"""
    
    @track_query_performance("venue_read")
    def get_venue(self, venue_id: int) -> Venue:
        """Get venue by ID using read replica"""
        with db_manager.get_session(role=DatabaseRole.REPLICA) as session:
            stmt = select(Venue).where(Venue.id == venue_id)
            result = session.execute(stmt)
            return result.scalar_one_or_none()
    
    @track_query_performance("venue_bulk_read")
    def get_venues_by_status(self, status: str, limit: int = 100) -> List[Venue]:
        """Get venues by status with limit"""
        with db_manager.get_session(role=DatabaseRole.REPLICA) as session:
            stmt = (
                select(Venue)
                .where(Venue.status == status)
                .limit(limit)
                .execution_options(populate_existing=True)
            )
            result = session.execute(stmt)
            return result.scalars().all()
    
    @track_query_performance("venue_update")
    async def update_venue_status(self, venue_id: int, status: str) -> bool:
        """Update venue status using primary connection"""
        async with db_manager.session(role=DatabaseRole.PRIMARY) as session:
            stmt = (
                select(Venue)
                .where(Venue.id == venue_id)
                .with_for_update(skip_locked=True)  # Prevent lock contention
            )
            result = await session.execute(stmt)
            venue = result.scalar_one_or_none()
            
            if venue:
                venue.status = status
                venue.updated_at = datetime.utcnow()
                await session.commit()
                return True
            return False
    
    @track_query_performance("venue_bulk_update")
    async def bulk_update_venues(self, venue_updates: List[dict]) -> int:
        """Bulk update venues with optimized performance"""
        updated_count = 0
        
        async with db_manager.transaction(isolation_level="READ COMMITTED") as session:
            for update in venue_updates:
                venue_id = update.get("id")
                new_status = update.get("status")
                
                if venue_id and new_status:
                    stmt = (
                        select(Venue)
                        .where(Venue.id == venue_id)
                        .with_for_update(skip_locked=True)
                    )
                    result = await session.execute(stmt)
                    venue = result.scalar_one_or_none()
                    
                    if venue:
                        venue.status = new_status
                        venue.updated_at = datetime.utcnow()
                        updated_count += 1
            
            await session.commit()
        
        return updated_count


class MonitoringRepository:
    """Repository for monitoring operations with time-series optimizations"""
    
    @track_query_performance("monitoring_insert")
    async def log_event(self, venue_id: int, event_type: str, event_data: dict):
        """Log monitoring event"""
        async with db_manager.session() as session:
            log = MonitoringLog(
                venue_id=venue_id,
                event_type=event_type,
                event_data=event_data,
            )
            session.add(log)
            await session.commit()
    
    @track_query_performance("monitoring_bulk_insert")
    async def bulk_log_events(self, events: List[dict]) -> int:
        """Bulk insert monitoring events"""
        return await db_manager.bulk_insert(
            MonitoringLog,
            events,
            batch_size=5000,  # Large batch for time-series data
        )
    
    @track_query_performance("monitoring_analytics")
    async def get_event_analytics(self, start_date: datetime, end_date: datetime):
        """Get event analytics using analytics connection"""
        async with db_manager.session(role=DatabaseRole.ANALYTICS, read_only=True) as session:
            # Complex analytics query that benefits from analytics-optimized connection
            stmt = text("""
                SELECT 
                    event_type,
                    DATE_TRUNC('hour', created_at) as hour,
                    COUNT(*) as event_count,
                    COUNT(DISTINCT venue_id) as unique_venues
                FROM monitoring_logs
                WHERE created_at BETWEEN :start_date AND :end_date
                GROUP BY event_type, hour
                ORDER BY hour DESC
            """)
            
            result = await session.execute(
                stmt,
                {"start_date": start_date, "end_date": end_date}
            )
            return result.fetchall()


# Performance testing utilities
async def stress_test_connections(num_requests: int = 1000):
    """Stress test connection pooling"""
    venue_repo = VenueRepository()
    tasks = []
    
    print(f"Starting stress test with {num_requests} concurrent requests...")
    start_time = time.time()
    
    for i in range(num_requests):
        # Mix of read and write operations
        if i % 10 == 0:
            # 10% writes
            task = venue_repo.update_venue_status(i % 100 + 1, "active")
        else:
            # 90% reads
            task = venue_repo.get_venue(i % 100 + 1)
        
        tasks.append(task)
    
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    duration = time.time() - start_time
    errors = [r for r in results if isinstance(r, Exception)]
    
    print(f"Completed {num_requests} requests in {duration:.2f} seconds")
    print(f"Throughput: {num_requests / duration:.2f} requests/second")
    print(f"Errors: {len(errors)}")
    
    if errors:
        print(f"Error types: {set(type(e).__name__ for e in errors)}")
    
    # Get performance metrics
    metrics = await db_manager.metrics.get_metrics_summary()
    print(f"\nPerformance Metrics:")
    for query_type, stats in metrics["query_performance"].items():
        print(f"  {query_type}:")
        print(f"    Count: {stats['count']}")
        print(f"    Avg: {stats['avg_ms']:.2f}ms")
        print(f"    Min: {stats['min_ms']:.2f}ms")
        print(f"    Max: {stats['max_ms']:.2f}ms")
        if stats.get('p95_ms'):
            print(f"    P95: {stats['p95_ms']:.2f}ms")


async def test_retry_logic():
    """Test connection retry logic"""
    print("Testing retry logic...")
    
    async def failing_operation():
        raise asyncpg.exceptions.TooManyConnectionsError("Test error")
    
    try:
        await db_manager.execute_with_retry(
            failing_operation,
            max_retries=3,
            retry_on={asyncpg.exceptions.TooManyConnectionsError}
        )
    except Exception as e:
        print(f"Operation failed after retries: {e}")


async def test_bulk_operations():
    """Test bulk insert performance"""
    print("Testing bulk operations...")
    
    monitoring_repo = MonitoringRepository()
    
    # Generate test data
    events = []
    for i in range(10000):
        events.append({
            "venue_id": i % 100 + 1,
            "event_type": f"event_{i % 10}",
            "event_data": {"value": i, "timestamp": datetime.utcnow().isoformat()},
        })
    
    start_time = time.time()
    inserted = await monitoring_repo.bulk_log_events(events)
    duration = time.time() - start_time
    
    print(f"Inserted {inserted} records in {duration:.2f} seconds")
    print(f"Throughput: {inserted / duration:.2f} records/second")


async def test_transaction_isolation():
    """Test transaction isolation levels"""
    print("Testing transaction isolation...")
    
    # Test SERIALIZABLE isolation for critical operations
    async with db_manager.transaction(
        isolation_level="SERIALIZABLE",
        read_only=False
    ) as session:
        # Perform operations that require strict consistency
        stmt = select(Venue).where(Venue.status == "pending").with_for_update()
        result = await session.execute(stmt)
        venues = result.scalars().all()
        
        for venue in venues:
            venue.status = "processed"
        
        await session.commit()
        print(f"Processed {len(venues)} venues with SERIALIZABLE isolation")


async def run_all_tests():
    """Run all test scenarios"""
    print("Initializing database...")
    await init_database()
    
    print("\n" + "="*50)
    print("Running Database Performance Tests")
    print("="*50 + "\n")
    
    # Check health
    health = await db_manager.health_check()
    print(f"Initial health check: {health['status']}")
    print(f"Connection pools: {health['engines']}\n")
    
    # Run tests
    await stress_test_connections(1000)
    print("\n" + "-"*50 + "\n")
    
    await test_bulk_operations()
    print("\n" + "-"*50 + "\n")
    
    await test_transaction_isolation()
    print("\n" + "-"*50 + "\n")
    
    await test_retry_logic()
    print("\n" + "-"*50 + "\n")
    
    # Final metrics
    final_metrics = await db_manager.metrics.get_metrics_summary()
    print("Final Performance Summary:")
    print(f"  Total errors: {sum(final_metrics['error_counts'].values())}")
    print(f"  Slow queries: {final_metrics['slow_queries_count']}")
    
    # Maintenance operations
    print("\nRunning maintenance operations...")
    await db_manager.analyze_tables(["venues", "monitoring_logs"])
    
    print("\nAll tests completed successfully!")


if __name__ == "__main__":
    # Run tests
    asyncio.run(run_all_tests())