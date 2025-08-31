"""
Data Aggregator Service
Manages data retrieval from multiple sources with priority and caching
Priority: Google Sheets -> Soundtrack API -> Gmail
"""

import logging
import asyncio
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from enum import Enum
import hashlib
import json

logger = logging.getLogger(__name__)

class DataSource(Enum):
    """Data source priority levels"""
    GOOGLE_SHEETS = 1  # Primary - venue master data
    SOUNDTRACK_API = 2  # Secondary - real-time status
    GMAIL = 3  # Tertiary - correspondence history
    DATABASE = 4  # Quaternary - local cache/backup

class DataAggregator:
    """
    Aggregates data from multiple sources with intelligent fallback
    Implements caching, circuit breaking, and source health monitoring
    """
    
    def __init__(self, 
                 sheets_client=None,
                 soundtrack_client=None,
                 gmail_client=None,
                 db_manager=None,
                 cache_manager=None):
        
        self.sheets_client = sheets_client
        self.soundtrack_client = soundtrack_client
        self.gmail_client = gmail_client
        self.db_manager = db_manager
        self.cache = cache_manager
        
        # Source health tracking
        self.source_health = {
            DataSource.GOOGLE_SHEETS: {'healthy': True, 'last_check': None, 'error_count': 0},
            DataSource.SOUNDTRACK_API: {'healthy': True, 'last_check': None, 'error_count': 0},
            DataSource.GMAIL: {'healthy': True, 'last_check': None, 'error_count': 0},
            DataSource.DATABASE: {'healthy': True, 'last_check': None, 'error_count': 0}
        }
        
        # Circuit breaker settings
        self.max_errors = 3
        self.health_check_interval = timedelta(minutes=5)
        
        # Cache TTL settings (in seconds)
        self.cache_ttl = {
            'venue_data': 3600,  # 1 hour for static venue data
            'zone_status': 300,  # 5 minutes for real-time status
            'search_results': 1800,  # 30 minutes for search results
            'email_history': 7200  # 2 hours for email data
        }
    
    async def get_venue_data(self, venue_id: Optional[int] = None, 
                           venue_name: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive venue data from all sources
        Aggregates and enriches data from multiple sources
        """
        # Create cache key
        cache_key = f"venue:{venue_id or venue_name}"
        
        # Check cache first
        if self.cache:
            cached_data = self.cache.get(cache_key)
            if cached_data:
                logger.info(f"Cache hit for venue: {venue_id or venue_name}")
                return json.loads(cached_data)
        
        venue_data = {}
        
        # Try sources in priority order
        for source in DataSource:
            if not self._is_source_healthy(source):
                continue
            
            try:
                if source == DataSource.GOOGLE_SHEETS:
                    data = await self._get_venue_from_sheets(venue_id, venue_name)
                    if data:
                        venue_data.update(data)
                        venue_data['primary_source'] = 'google_sheets'
                
                elif source == DataSource.SOUNDTRACK_API:
                    if 'soundtrack_account_id' in venue_data:
                        status_data = await self._get_venue_status_from_soundtrack(
                            venue_data['soundtrack_account_id']
                        )
                        if status_data:
                            venue_data['real_time_status'] = status_data
                            venue_data['status_source'] = 'soundtrack_api'
                
                elif source == DataSource.GMAIL:
                    if 'contact_email' in venue_data:
                        email_data = await self._get_venue_emails(venue_data['contact_email'])
                        if email_data:
                            venue_data['recent_communications'] = email_data
                            venue_data['communication_source'] = 'gmail'
                
                elif source == DataSource.DATABASE:
                    if not venue_data:  # Only use database as last resort
                        db_data = await self._get_venue_from_database(venue_id, venue_name)
                        if db_data:
                            venue_data.update(db_data)
                            venue_data['primary_source'] = 'database'
                
            except Exception as e:
                logger.error(f"Error fetching from {source.name}: {e}")
                self._record_source_error(source)
        
        # Cache the aggregated data
        if venue_data and self.cache:
            self.cache.setex(
                cache_key,
                self.cache_ttl['venue_data'],
                json.dumps(venue_data)
            )
        
        return venue_data if venue_data else None
    
    async def get_zone_status(self, venue_id: int) -> Dict[str, Any]:
        """
        Get real-time zone status for a venue
        Prioritizes Soundtrack API for real-time data
        """
        cache_key = f"zone_status:{venue_id}"
        
        # Check cache
        if self.cache:
            cached_status = self.cache.get(cache_key)
            if cached_status:
                return json.loads(cached_status)
        
        status_data = {
            'venue_id': venue_id,
            'zones': [],
            'last_updated': datetime.utcnow().isoformat(),
            'overall_status': 'unknown'
        }
        
        # Try to get venue's Soundtrack account ID
        venue_data = await self.get_venue_data(venue_id=venue_id)
        if not venue_data or 'soundtrack_account_id' not in venue_data:
            logger.warning(f"No Soundtrack account found for venue {venue_id}")
            return status_data
        
        # Get real-time status from Soundtrack
        if self._is_source_healthy(DataSource.SOUNDTRACK_API):
            try:
                zones = await self._get_zones_from_soundtrack(venue_data['soundtrack_account_id'])
                if zones:
                    status_data['zones'] = zones
                    
                    # Calculate overall status
                    active_zones = sum(1 for z in zones if z.get('status') == 'playing')
                    total_zones = len(zones)
                    
                    if total_zones == 0:
                        status_data['overall_status'] = 'no_zones'
                    elif active_zones == total_zones:
                        status_data['overall_status'] = 'all_active'
                    elif active_zones == 0:
                        status_data['overall_status'] = 'all_inactive'
                    else:
                        status_data['overall_status'] = 'partial_active'
                    
                    status_data['active_zones'] = active_zones
                    status_data['total_zones'] = total_zones
                    
                    # Cache the status
                    if self.cache:
                        self.cache.setex(
                            cache_key,
                            self.cache_ttl['zone_status'],
                            json.dumps(status_data)
                        )
                
            except Exception as e:
                logger.error(f"Error getting zone status: {e}")
                self._record_source_error(DataSource.SOUNDTRACK_API)
        
        # Fallback to database if Soundtrack API fails
        if not status_data['zones'] and self._is_source_healthy(DataSource.DATABASE):
            try:
                db_zones = await self._get_zones_from_database(venue_id)
                if db_zones:
                    status_data['zones'] = db_zones
                    status_data['source'] = 'database'
                    status_data['note'] = 'Real-time data unavailable, showing last known status'
            except Exception as e:
                logger.error(f"Error getting zones from database: {e}")
        
        return status_data
    
    def search_venues(self, name_query: str, phone_number: Optional[str] = None) -> List[Dict[str, Any]]:
        """
        Search for venues across all data sources
        Returns list of matches with confidence scores
        """
        cache_key = f"search:{name_query}:{phone_number or ''}"
        
        # Check cache
        if self.cache:
            cached_results = self.cache.get(cache_key)
            if cached_results:
                return json.loads(cached_results)
        
        all_results = []
        seen_venues = set()  # Track unique venues
        
        # Search each source
        for source in DataSource:
            if not self._is_source_healthy(source):
                continue
            
            try:
                if source == DataSource.GOOGLE_SHEETS:
                    results = self._search_sheets(name_query, phone_number)
                    for result in results:
                        venue_key = f"{result['name']}:{result.get('location', '')}"
                        if venue_key not in seen_venues:
                            result['source'] = 'google_sheets'
                            all_results.append(result)
                            seen_venues.add(venue_key)
                
                elif source == DataSource.DATABASE:
                    results = self._search_database(name_query, phone_number)
                    for result in results:
                        venue_key = f"{result['name']}:{result.get('location', '')}"
                        if venue_key not in seen_venues:
                            result['source'] = 'database'
                            all_results.append(result)
                            seen_venues.add(venue_key)
                
            except Exception as e:
                logger.error(f"Search error in {source.name}: {e}")
                self._record_source_error(source)
        
        # Sort by confidence score
        all_results.sort(key=lambda x: x.get('confidence', 0), reverse=True)
        
        # Cache results
        if all_results and self.cache:
            self.cache.setex(
                cache_key,
                self.cache_ttl['search_results'],
                json.dumps(all_results[:10])  # Cache top 10 results
            )
        
        return all_results
    
    async def sync_venue_data(self, venue_id: int) -> bool:
        """
        Synchronize venue data across all sources
        Updates local database with latest data from primary sources
        """
        try:
            # Get latest data from all sources
            venue_data = await self.get_venue_data(venue_id=venue_id)
            
            if not venue_data:
                logger.warning(f"No data found for venue {venue_id}")
                return False
            
            # Update database with latest data
            if self.db_manager:
                success = await self._update_database_venue(venue_id, venue_data)
                if success:
                    logger.info(f"Successfully synced venue {venue_id}")
                    
                    # Invalidate cache to force fresh data
                    if self.cache:
                        self.cache.delete(f"venue:{venue_id}")
                    
                    return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error syncing venue {venue_id}: {e}")
            return False
    
    # Source-specific methods (implementations would connect to actual APIs)
    
    async def _get_venue_from_sheets(self, venue_id: Optional[int], venue_name: Optional[str]) -> Optional[Dict]:
        """Get venue data from Google Sheets"""
        if not self.sheets_client:
            return None
        
        try:
            return await self.sheets_client.get_venue(venue_id, venue_name)
        except Exception as e:
            logger.error(f"Sheets error: {e}")
            raise
    
    async def _get_venue_status_from_soundtrack(self, account_id: str) -> Optional[Dict]:
        """Get real-time status from Soundtrack API"""
        if not self.soundtrack_client:
            return None
        
        try:
            return await self.soundtrack_client.get_account_status(account_id)
        except Exception as e:
            logger.error(f"Soundtrack API error: {e}")
            raise
    
    async def _get_zones_from_soundtrack(self, account_id: str) -> List[Dict]:
        """Get zones from Soundtrack API"""
        if not self.soundtrack_client:
            return []
        
        try:
            return await self.soundtrack_client.get_zones(account_id)
        except Exception as e:
            logger.error(f"Soundtrack zones error: {e}")
            raise
    
    async def _get_venue_emails(self, email: str) -> List[Dict]:
        """Get recent emails for venue"""
        if not self.gmail_client:
            return []
        
        try:
            return await self.gmail_client.search_emails(email, limit=10)
        except Exception as e:
            logger.error(f"Gmail error: {e}")
            raise
    
    async def _get_venue_from_database(self, venue_id: Optional[int], venue_name: Optional[str]) -> Optional[Dict]:
        """Get venue from local database"""
        if not self.db_manager:
            return None
        
        try:
            return await self.db_manager.get_venue(venue_id, venue_name)
        except Exception as e:
            logger.error(f"Database error: {e}")
            raise
    
    async def _get_zones_from_database(self, venue_id: int) -> List[Dict]:
        """Get zones from database"""
        if not self.db_manager:
            return []
        
        try:
            return await self.db_manager.get_zones(venue_id)
        except Exception as e:
            logger.error(f"Database zones error: {e}")
            raise
    
    def _search_sheets(self, query: str, phone: Optional[str]) -> List[Dict]:
        """Search Google Sheets"""
        if not self.sheets_client:
            return []
        
        try:
            return self.sheets_client.search_venues(query, phone)
        except Exception as e:
            logger.error(f"Sheets search error: {e}")
            return []
    
    def _search_database(self, query: str, phone: Optional[str]) -> List[Dict]:
        """Search local database"""
        if not self.db_manager:
            return []
        
        try:
            return self.db_manager.search_venues(query, phone)
        except Exception as e:
            logger.error(f"Database search error: {e}")
            return []
    
    async def _update_database_venue(self, venue_id: int, data: Dict) -> bool:
        """Update database with venue data"""
        if not self.db_manager:
            return False
        
        try:
            return await self.db_manager.update_venue(venue_id, data)
        except Exception as e:
            logger.error(f"Database update error: {e}")
            return False
    
    def _is_source_healthy(self, source: DataSource) -> bool:
        """Check if a data source is healthy"""
        health = self.source_health[source]
        
        # Check if we should retry after cooldown
        if not health['healthy'] and health['last_check']:
            time_since_check = datetime.utcnow() - health['last_check']
            if time_since_check > self.health_check_interval:
                # Reset health check
                health['healthy'] = True
                health['error_count'] = 0
                logger.info(f"Resetting health check for {source.name}")
        
        return health['healthy']
    
    def _record_source_error(self, source: DataSource):
        """Record an error for a data source"""
        health = self.source_health[source]
        health['error_count'] += 1
        health['last_check'] = datetime.utcnow()
        
        if health['error_count'] >= self.max_errors:
            health['healthy'] = False
            logger.warning(f"Data source {source.name} marked unhealthy after {self.max_errors} errors")
    
    def get_source_health_status(self) -> Dict[str, Any]:
        """Get health status of all data sources"""
        status = {}
        for source in DataSource:
            health = self.source_health[source]
            status[source.name] = {
                'healthy': health['healthy'],
                'error_count': health['error_count'],
                'last_check': health['last_check'].isoformat() if health['last_check'] else None
            }
        return status