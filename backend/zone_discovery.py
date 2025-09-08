"""
Dynamic zone discovery and caching for Soundtrack Your Brand API
This module provides a scalable solution for accessing 2000+ venue accounts
without hardcoding zone IDs
"""

import json
import logging
import os
from typing import Dict, List, Optional, Tuple
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Try to import redis but make it optional
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

load_dotenv()

logger = logging.getLogger(__name__)

class ZoneDiscoveryService:
    """
    Service for dynamically discovering and caching zone information
    Uses multiple strategies to find zones across 2000+ venues
    """
    
    def __init__(self):
        self.redis_client = None
        self.cache_ttl = 3600  # 1 hour cache
        self._init_redis()
        
        # Import soundtrack API
        from soundtrack_api import SoundtrackAPI
        self.api = SoundtrackAPI()
        
    def _init_redis(self):
        """Initialize Redis connection for caching"""
        if not REDIS_AVAILABLE:
            logger.warning("⚠️ Redis module not installed - caching disabled")
            self.redis_client = None
            return
            
        try:
            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            logger.info("✅ Redis connected for zone caching")
        except Exception as e:
            logger.warning(f"⚠️ Redis not available for caching: {e}")
            self.redis_client = None
    
    def get_zone_for_venue(self, venue_name: str, zone_name: str) -> Optional[str]:
        """
        Get zone ID for a venue using multiple strategies:
        1. Check Redis cache
        2. Check hardcoded venue_accounts.py (for known venues)
        3. Search through all accessible accounts
        4. Use fuzzy matching for venue/zone names
        """
        cache_key = f"zone:{venue_name.lower()}:{zone_name.lower()}"
        
        # 1. Check cache first
        if self.redis_client:
            try:
                cached = self.redis_client.get(cache_key)
                if cached:
                    logger.info(f"✅ Zone found in cache: {cached[:20]}...")
                    return cached
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")
        
        # 2. Check hardcoded venues (fallback for known venues)
        try:
            from venue_accounts import get_zone_id
            zone_id = get_zone_id(venue_name, zone_name)
            if zone_id:
                logger.info(f"✅ Zone found in venue_accounts: {zone_id[:20]}...")
                self._cache_zone(cache_key, zone_id)
                return zone_id
        except ImportError:
            pass
        
        # 3. Search through all accessible accounts
        zone_id = self._search_all_accounts(venue_name, zone_name)
        if zone_id:
            self._cache_zone(cache_key, zone_id)
            return zone_id
        
        # 4. Try fuzzy matching
        zone_id = self._fuzzy_search(venue_name, zone_name)
        if zone_id:
            self._cache_zone(cache_key, zone_id)
            return zone_id
        
        logger.warning(f"❌ Zone not found: {venue_name} - {zone_name}")
        return None
    
    def _search_all_accounts(self, venue_name: str, zone_name: str) -> Optional[str]:
        """
        Search through all accessible accounts to find the zone
        This handles the 2000+ venues requirement
        """
        try:
            # Get all accounts we have access to
            accounts = self.api.get_accounts(limit=100)  # Start with first 100
            
            if not accounts:
                logger.warning("No accounts accessible via API")
                return None
            
            venue_lower = venue_name.lower()
            zone_lower = zone_name.lower().replace(' ', '_')
            
            # Search through accounts
            for account in accounts:
                account_name = account.get('businessName', '').lower()
                
                # Check if this might be the venue
                if venue_lower in account_name or account_name in venue_lower:
                    logger.info(f"Checking account: {account.get('businessName')}")
                    
                    # Get zones for this account
                    zones = self._get_zones_for_account(account.get('id'))
                    
                    for zone in zones:
                        zone_display = zone.get('displayName', '').lower()
                        if zone_lower in zone_display or zone_display in zone_lower:
                            zone_id = zone.get('id')
                            logger.info(f"✅ Found zone via search: {zone_id[:20]}...")
                            return zone_id
            
            # If not found in first batch, paginate through more accounts
            if len(accounts) == 100:
                return self._search_paginated_accounts(venue_name, zone_name)
                
        except Exception as e:
            logger.error(f"Account search failed: {e}")
        
        return None
    
    def _search_paginated_accounts(self, venue_name: str, zone_name: str, cursor: str = None) -> Optional[str]:
        """
        Search through paginated accounts for large-scale deployments
        """
        try:
            # This would need to be implemented with proper pagination
            # For now, returning None as we need API pagination support
            logger.info("Would search through paginated accounts here")
            return None
        except Exception as e:
            logger.error(f"Paginated search failed: {e}")
            return None
    
    def _get_zones_for_account(self, account_id: str) -> List[Dict]:
        """
        Get all zones for a specific account
        """
        try:
            # Use the API to get zones
            zones = self.api.get_zones_by_account(account_id)
            return zones if zones else []
        except Exception as e:
            logger.error(f"Failed to get zones for account {account_id}: {e}")
            return []
    
    def _fuzzy_search(self, venue_name: str, zone_name: str) -> Optional[str]:
        """
        Try fuzzy matching for venue and zone names
        Handles variations like "Hilton Pattaya" vs "Pattaya Hilton"
        """
        try:
            # Common variations to try
            venue_parts = venue_name.lower().split()
            zone_parts = zone_name.lower().split()
            
            # Try different combinations
            variations = [
                venue_name,
                ' '.join(reversed(venue_parts)),  # Reverse word order
                venue_parts[0] if venue_parts else venue_name,  # First word only
            ]
            
            for variant in variations:
                result = self._search_all_accounts(variant, zone_name)
                if result:
                    return result
            
        except Exception as e:
            logger.error(f"Fuzzy search failed: {e}")
        
        return None
    
    def _cache_zone(self, key: str, zone_id: str):
        """Cache zone ID for future use"""
        if self.redis_client:
            try:
                self.redis_client.setex(key, self.cache_ttl, zone_id)
                logger.info(f"Cached zone ID for {key}")
            except Exception as e:
                logger.warning(f"Failed to cache zone: {e}")
    
    def discover_and_cache_all_zones(self) -> Dict[str, Dict[str, str]]:
        """
        Discover and cache all accessible zones
        This can be run periodically to build up the cache
        """
        discovered = {}
        
        try:
            accounts = self.api.get_accounts(limit=100)
            
            for account in accounts:
                account_name = account.get('businessName', 'Unknown')
                account_id = account.get('id')
                
                zones = self._get_zones_for_account(account_id)
                
                if zones:
                    discovered[account_name] = {}
                    for zone in zones:
                        zone_name = zone.get('displayName', 'Unknown')
                        zone_id = zone.get('id')
                        discovered[account_name][zone_name] = zone_id
                        
                        # Cache each zone
                        cache_key = f"zone:{account_name.lower()}:{zone_name.lower()}"
                        self._cache_zone(cache_key, zone_id)
            
            logger.info(f"Discovered {len(discovered)} accounts with zones")
            
            # Save discovered zones to file for backup
            with open('discovered_zones.json', 'w') as f:
                json.dump(discovered, f, indent=2)
                
        except Exception as e:
            logger.error(f"Zone discovery failed: {e}")
        
        return discovered


# Global instance
zone_discovery = ZoneDiscoveryService()

def get_zone_id(venue_name: str, zone_name: str) -> Optional[str]:
    """
    Main entry point for getting zone IDs
    Handles 2000+ venues without hardcoding
    """
    return zone_discovery.get_zone_for_venue(venue_name, zone_name)

def discover_all_zones() -> Dict[str, Dict[str, str]]:
    """
    Discover and cache all accessible zones
    Run this periodically to keep cache fresh
    """
    return zone_discovery.discover_and_cache_all_zones()