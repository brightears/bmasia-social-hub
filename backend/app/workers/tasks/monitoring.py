"""
Zone Monitoring Worker for BMA Social Platform

Handles continuous monitoring of music zones across all venues.
Designed for 10,000+ zones with intelligent batching and alerting.
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, List
from sqlalchemy import select, update
from sqlalchemy.orm import selectinload

from app.workers.celery_app import celery_app
from app.core.database import db_manager
from app.core.redis import redis_manager
from app.models.zone import Zone, ZoneStatus
from app.models.venue import Venue
from app.models.monitoring import MonitoringLog, AlertType, AlertSeverity
from app.services.soundtrack.client import soundtrack_client

logger = logging.getLogger(__name__)


@celery_app.task(name="app.workers.tasks.monitoring.check_all_zones")
def check_all_zones():
    """
    Periodic task to check status of all active zones.
    Runs every 5 minutes via Celery beat.
    """
    _check_all_zones()


def _check_all_zones():
    """Async implementation of zone checking"""
    logger.info("Starting zone monitoring check")
    
    start_time = datetime.utcnow()
    
    with db_manager.get_session() as session:
        # Get all active zones grouped by venue
        result = session.execute(
            select(Zone)
            .options(selectinload(Zone.venue))
            .where(Zone.is_active == True)
            .where(Zone.monitoring_enabled == True)
        )
        zones = result.scalars().all()
        
        logger.info(f"Monitoring {len(zones)} active zones")
        
        # Batch zones for efficient API calls
        batch_size = 50
        total_issues = 0
        
        for i in range(0, len(zones), batch_size):
            batch = zones[i:i + batch_size]
            zone_ids = [str(zone.soundtrack_device_id) for zone in batch]
            
            # Get status for batch
            # Note: Soundtrack client operations may still be async, check client implementation
            statuses = soundtrack_client.batch_get_device_status(zone_ids)
            
            # Process results
            for zone, status in zip(batch, statuses):
                if isinstance(status, dict) and not status.get("error"):
                    # Update zone status
                    _update_zone_status(session, zone, status)
                    
                    # Check for issues
                    if not status.get("is_playing") and zone.should_be_playing:
                        _handle_zone_issue(session, zone, "not_playing")
                        total_issues += 1
                    elif status.get("volume", 0) == 0 and zone.should_be_playing:
                        _handle_zone_issue(session, zone, "muted")
                        total_issues += 1
                else:
                    # Device offline or error
                    _handle_zone_issue(session, zone, "offline")
                    total_issues += 1
        
        session.commit()
    
    # Log monitoring completion
    duration = (datetime.utcnow() - start_time).total_seconds()
    
    await redis_manager.publish(
        "monitoring:completed",
        {
            "zones_checked": len(zones),
            "issues_found": total_issues,
            "duration_seconds": duration,
            "timestamp": datetime.utcnow().isoformat(),
        }
    )
    
    logger.info(f"Zone monitoring completed: {len(zones)} zones, {total_issues} issues, {duration:.2f}s")


def _update_zone_status(session, zone: Zone, status: Dict[str, Any]):
    """Update zone status in database"""
    session.execute(
        update(Zone)
        .where(Zone.id == zone.id)
        .values(
            current_status=ZoneStatus.PLAYING if status.get("is_playing") else ZoneStatus.STOPPED,
            current_volume=status.get("volume"),
            current_playlist_id=status.get("playlist_id"),
            last_seen_online=datetime.utcnow() if not status.get("error") else zone.last_seen_online,
            last_status_check=datetime.utcnow(),
        )
    )
    
    # Cache status
    await redis_manager.setex(
        f"zone:status:{zone.id}",
        60,  # 1 minute cache
        status
    )


def _handle_zone_issue(session, zone: Zone, issue_type: str):
    """Handle detected zone issue"""
    # Check if alert already exists
    cooldown_key = f"alert:cooldown:{zone.id}:{issue_type}"
    if await redis_manager.exists(cooldown_key):
        return  # Skip if in cooldown
    
    # Create monitoring log
    log = MonitoringLog(
        zone_id=zone.id,
        venue_id=zone.venue_id,
        event_type=f"zone_{issue_type}",
        event_data={
            "zone_name": zone.name,
            "issue": issue_type,
            "detected_at": datetime.utcnow().isoformat(),
        },
        severity=AlertSeverity.HIGH if issue_type == "offline" else AlertSeverity.MEDIUM,
    )
    session.add(log)
    
    # Set cooldown
    await redis_manager.setex(cooldown_key, 3600, "1")  # 1 hour cooldown
    
    # Publish alert
    await redis_manager.publish(
        "alerts:zone_issue",
        {
            "zone_id": str(zone.id),
            "venue_id": str(zone.venue_id),
            "zone_name": zone.name,
            "venue_name": zone.venue.name,
            "issue": issue_type,
            "severity": "high" if issue_type == "offline" else "medium",
            "timestamp": datetime.utcnow().isoformat(),
        }
    )


@celery_app.task(name="app.workers.tasks.monitoring.cleanup_old_logs")
def cleanup_old_logs():
    """Clean up old monitoring logs to manage database size"""
    asyncio.run(_cleanup_old_logs())


async def _cleanup_old_logs():
    """Remove monitoring logs older than 30 days"""
    logger.info("Starting cleanup of old monitoring logs")
    
    cutoff_date = datetime.utcnow() - timedelta(days=30)
    
    async with get_async_session() as session:
        # Delete old logs
        result = await session.execute(
            "DELETE FROM monitoring_logs WHERE created_at < :cutoff",
            {"cutoff": cutoff_date}
        )
        
        deleted_count = result.rowcount
        await session.commit()
    
    logger.info(f"Deleted {deleted_count} old monitoring logs")
    
    return {"deleted": deleted_count}