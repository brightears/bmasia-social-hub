"""
Sync Manager for BMA Social Platform
Manages data synchronization across all sources
"""

import logging
import asyncio
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from enum import Enum
import json

logger = logging.getLogger(__name__)

class SyncStrategy(Enum):
    """Synchronization strategies"""
    REAL_TIME = "real_time"  # Sync immediately on change
    PERIODIC = "periodic"  # Sync at regular intervals
    ON_DEMAND = "on_demand"  # Sync when requested
    LAZY = "lazy"  # Sync only when data is accessed

class SyncManager:
    """
    Manages data synchronization across Google Sheets, Gmail, Soundtrack API, and local database
    Implements intelligent sync strategies based on data type and usage patterns
    """
    
    def __init__(self,
                 data_aggregator=None,
                 db_manager=None,
                 cache_manager=None):
        
        self.data_aggregator = data_aggregator
        self.db_manager = db_manager
        self.cache = cache_manager
        
        # Sync configuration
        self.sync_config = {
            'venue_master': {
                'strategy': SyncStrategy.PERIODIC,
                'interval': timedelta(hours=1),
                'last_sync': None,
                'priority': 1
            },
            'zone_status': {
                'strategy': SyncStrategy.REAL_TIME,
                'interval': timedelta(minutes=5),
                'last_sync': None,
                'priority': 2
            },
            'email_history': {
                'strategy': SyncStrategy.LAZY,
                'interval': timedelta(hours=2),
                'last_sync': None,
                'priority': 3
            },
            'performance_metrics': {
                'strategy': SyncStrategy.PERIODIC,
                'interval': timedelta(minutes=15),
                'last_sync': None,
                'priority': 2
            }
        }
        
        # Sync status tracking
        self.sync_status = {
            'running': False,
            'last_full_sync': None,
            'venues_synced': 0,
            'errors': []
        }
        
        # Queue for sync tasks
        self.sync_queue = asyncio.Queue()
        self.processing_task = None
    
    async def start_sync_scheduler(self):
        """Start the background sync scheduler"""
        if self.processing_task:
            logger.warning("Sync scheduler already running")
            return
        
        self.sync_status['running'] = True
        self.processing_task = asyncio.create_task(self._sync_processor())
        logger.info("Sync scheduler started")
        
        # Schedule initial syncs
        await self._schedule_periodic_syncs()
    
    async def stop_sync_scheduler(self):
        """Stop the background sync scheduler"""
        self.sync_status['running'] = False
        
        if self.processing_task:
            self.processing_task.cancel()
            try:
                await self.processing_task
            except asyncio.CancelledError:
                pass
            self.processing_task = None
        
        logger.info("Sync scheduler stopped")
    
    async def _sync_processor(self):
        """Process sync tasks from the queue"""
        while self.sync_status['running']:
            try:
                # Get next sync task
                task = await asyncio.wait_for(
                    self.sync_queue.get(),
                    timeout=1.0
                )
                
                # Execute sync task
                await self._execute_sync_task(task)
                
            except asyncio.TimeoutError:
                continue
            except Exception as e:
                logger.error(f"Error in sync processor: {e}")
                self.sync_status['errors'].append({
                    'timestamp': datetime.utcnow().isoformat(),
                    'error': str(e)
                })
    
    async def _schedule_periodic_syncs(self):
        """Schedule periodic sync tasks"""
        while self.sync_status['running']:
            try:
                current_time = datetime.utcnow()
                
                for sync_type, config in self.sync_config.items():
                    if config['strategy'] != SyncStrategy.PERIODIC:
                        continue
                    
                    # Check if sync is due
                    if config['last_sync'] is None or \
                       (current_time - config['last_sync']) >= config['interval']:
                        
                        # Add to sync queue
                        await self.sync_queue.put({
                            'type': sync_type,
                            'priority': config['priority'],
                            'requested_at': current_time
                        })
                        
                        config['last_sync'] = current_time
                
                # Wait before next check
                await asyncio.sleep(60)  # Check every minute
                
            except Exception as e:
                logger.error(f"Error in periodic sync scheduler: {e}")
                await asyncio.sleep(60)
    
    async def _execute_sync_task(self, task: Dict[str, Any]):
        """Execute a specific sync task"""
        sync_type = task['type']
        logger.info(f"Executing sync task: {sync_type}")
        
        try:
            if sync_type == 'venue_master':
                await self.sync_venue_master_data()
            
            elif sync_type == 'zone_status':
                await self.sync_zone_status()
            
            elif sync_type == 'email_history':
                await self.sync_email_history()
            
            elif sync_type == 'performance_metrics':
                await self.sync_performance_metrics()
            
            elif sync_type == 'full_sync':
                await self.perform_full_sync()
            
            else:
                logger.warning(f"Unknown sync type: {sync_type}")
            
        except Exception as e:
            logger.error(f"Error executing sync task {sync_type}: {e}")
            self.sync_status['errors'].append({
                'timestamp': datetime.utcnow().isoformat(),
                'task': sync_type,
                'error': str(e)
            })
    
    async def sync_venue_master_data(self):
        """Sync venue master data from Google Sheets to database"""
        if not self.data_aggregator:
            logger.warning("Data aggregator not available")
            return
        
        logger.info("Starting venue master data sync")
        
        try:
            # Get all venues from Google Sheets
            if hasattr(self.data_aggregator, 'sheets_client') and self.data_aggregator.sheets_client:
                venues = self.data_aggregator.sheets_client.get_all_venues()
                
                synced_count = 0
                for venue in venues:
                    # Update database
                    if self.db_manager:
                        success = await self.db_manager.upsert_venue(venue)
                        if success:
                            synced_count += 1
                    
                    # Update cache
                    if self.cache:
                        cache_key = f"venue:{venue.get('venue_id')}"
                        self.cache.setex(cache_key, 3600, json.dumps(venue))
                
                self.sync_status['venues_synced'] = synced_count
                logger.info(f"Synced {synced_count} venues from Google Sheets")
            
        except Exception as e:
            logger.error(f"Error syncing venue master data: {e}")
            raise
    
    async def sync_zone_status(self):
        """Sync real-time zone status from Soundtrack API"""
        if not self.data_aggregator or not self.db_manager:
            return
        
        logger.info("Starting zone status sync")
        
        try:
            # Get all venues
            venues = await self.db_manager.get_all_venues()
            
            for venue in venues:
                if not venue.get('soundtrack_account_id'):
                    continue
                
                # Get real-time status
                status = await self.data_aggregator.get_zone_status(venue['id'])
                
                if status and status.get('zones'):
                    # Update database with zone status
                    for zone in status['zones']:
                        await self.db_manager.update_zone_status(
                            zone_id=zone['id'],
                            status=zone.get('status'),
                            last_check=datetime.utcnow()
                        )
                    
                    # Cache the status
                    if self.cache:
                        cache_key = f"zone_status:{venue['id']}"
                        self.cache.setex(cache_key, 300, json.dumps(status))
            
            logger.info("Zone status sync completed")
            
        except Exception as e:
            logger.error(f"Error syncing zone status: {e}")
            raise
    
    async def sync_email_history(self):
        """Sync email history from Gmail"""
        if not self.data_aggregator:
            return
        
        logger.info("Starting email history sync")
        
        try:
            # This would typically sync recent emails for all venues
            # For now, just log the action
            logger.info("Email history sync would process venue communications")
            
        except Exception as e:
            logger.error(f"Error syncing email history: {e}")
            raise
    
    async def sync_performance_metrics(self):
        """Sync performance metrics and analytics"""
        logger.info("Starting performance metrics sync")
        
        try:
            # Calculate and store performance metrics
            if self.db_manager:
                metrics = await self.db_manager.calculate_performance_metrics()
                
                # Cache metrics
                if self.cache and metrics:
                    self.cache.setex(
                        "performance_metrics",
                        900,  # 15 minutes
                        json.dumps(metrics)
                    )
                
                logger.info("Performance metrics updated")
            
        except Exception as e:
            logger.error(f"Error syncing performance metrics: {e}")
            raise
    
    async def perform_full_sync(self):
        """Perform a full synchronization of all data sources"""
        logger.info("Starting full system sync")
        start_time = datetime.utcnow()
        
        self.sync_status['last_full_sync'] = start_time
        errors = []
        
        # Sync in priority order
        sync_tasks = [
            ('venue_master', self.sync_venue_master_data),
            ('zone_status', self.sync_zone_status),
            ('email_history', self.sync_email_history),
            ('performance_metrics', self.sync_performance_metrics)
        ]
        
        for task_name, task_func in sync_tasks:
            try:
                await task_func()
                logger.info(f"Completed sync: {task_name}")
            except Exception as e:
                logger.error(f"Failed sync: {task_name} - {e}")
                errors.append({'task': task_name, 'error': str(e)})
        
        # Update sync status
        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()
        
        logger.info(f"Full sync completed in {duration:.2f} seconds with {len(errors)} errors")
        
        return {
            'success': len(errors) == 0,
            'duration': duration,
            'errors': errors,
            'timestamp': end_time.isoformat()
        }
    
    async def request_sync(self, sync_type: str, priority: int = 2):
        """Request a specific sync operation"""
        await self.sync_queue.put({
            'type': sync_type,
            'priority': priority,
            'requested_at': datetime.utcnow()
        })
        
        logger.info(f"Sync requested: {sync_type} (priority: {priority})")
    
    def get_sync_status(self) -> Dict[str, Any]:
        """Get current sync status"""
        status = {
            'running': self.sync_status['running'],
            'last_full_sync': self.sync_status['last_full_sync'].isoformat() \
                             if self.sync_status['last_full_sync'] else None,
            'venues_synced': self.sync_status['venues_synced'],
            'recent_errors': self.sync_status['errors'][-5:],  # Last 5 errors
            'sync_config': {}
        }
        
        # Add sync configuration status
        for sync_type, config in self.sync_config.items():
            status['sync_config'][sync_type] = {
                'strategy': config['strategy'].value,
                'interval_minutes': config['interval'].total_seconds() / 60,
                'last_sync': config['last_sync'].isoformat() if config['last_sync'] else None,
                'next_sync': (config['last_sync'] + config['interval']).isoformat() \
                           if config['last_sync'] else None
            }
        
        return status
    
    async def validate_data_consistency(self) -> Dict[str, Any]:
        """Validate data consistency across all sources"""
        logger.info("Starting data consistency validation")
        
        inconsistencies = []
        
        try:
            if not self.data_aggregator or not self.db_manager:
                return {'success': False, 'message': 'Required components not available'}
            
            # Get venues from different sources
            sheets_venues = []
            db_venues = []
            
            if hasattr(self.data_aggregator, 'sheets_client') and self.data_aggregator.sheets_client:
                sheets_venues = self.data_aggregator.sheets_client.get_all_venues()
            
            if self.db_manager:
                db_venues = await self.db_manager.get_all_venues()
            
            # Compare venue counts
            if len(sheets_venues) != len(db_venues):
                inconsistencies.append({
                    'type': 'venue_count_mismatch',
                    'sheets_count': len(sheets_venues),
                    'database_count': len(db_venues)
                })
            
            # Check individual venues
            sheets_by_id = {v.get('venue_id'): v for v in sheets_venues if v.get('venue_id')}
            db_by_id = {v.get('id'): v for v in db_venues}
            
            # Find missing venues
            sheets_ids = set(sheets_by_id.keys())
            db_ids = set(db_by_id.keys())
            
            missing_in_db = sheets_ids - db_ids
            missing_in_sheets = db_ids - sheets_ids
            
            if missing_in_db:
                inconsistencies.append({
                    'type': 'missing_in_database',
                    'venue_ids': list(missing_in_db)
                })
            
            if missing_in_sheets:
                inconsistencies.append({
                    'type': 'missing_in_sheets',
                    'venue_ids': list(missing_in_sheets)
                })
            
            # Check field consistency for common venues
            for venue_id in sheets_ids & db_ids:
                sheets_venue = sheets_by_id[venue_id]
                db_venue = db_by_id[venue_id]
                
                # Check critical fields
                critical_fields = ['venue_name', 'soundtrack_account_id', 'contact_email']
                for field in critical_fields:
                    sheets_value = sheets_venue.get(field)
                    db_value = db_venue.get(field if field != 'venue_name' else 'name')
                    
                    if sheets_value != db_value:
                        inconsistencies.append({
                            'type': 'field_mismatch',
                            'venue_id': venue_id,
                            'field': field,
                            'sheets_value': sheets_value,
                            'database_value': db_value
                        })
            
            return {
                'success': len(inconsistencies) == 0,
                'inconsistencies': inconsistencies,
                'checked_at': datetime.utcnow().isoformat()
            }
            
        except Exception as e:
            logger.error(f"Error validating data consistency: {e}")
            return {
                'success': False,
                'error': str(e)
            }