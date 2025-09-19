"""
Hybrid venue manager that supports both database and file-based operations
Provides seamless transition from venue_data.md to PostgreSQL
"""

import os
import asyncio
import logging
from typing import Dict, Optional, List, Tuple
from venue_manager import VenueManager as FileVenueManager

logger = logging.getLogger(__name__)


class HybridVenueManager:
    """
    Venue manager with dual-mode support:
    - Database mode: Uses PostgreSQL with Redis caching (fast, scalable)
    - File mode: Falls back to venue_data.md (backward compatible)
    """

    def __init__(self):
        self.use_database = os.getenv("USE_DATABASE", "false").lower() == "true"
        self.file_manager = FileVenueManager()
        self.db_manager = None
        self._db_initialized = False

    async def initialize(self):
        """Initialize the venue manager"""
        if self.use_database and not self._db_initialized:
            try:
                from database_manager import get_database_manager
                self.db_manager = await get_database_manager()
                self._db_initialized = True
                logger.info("Hybrid venue manager initialized in DATABASE mode")

                # Warm cache with top venues
                await self.db_manager.warm_cache(top_venues=100)

            except Exception as e:
                logger.error(f"Failed to initialize database mode, falling back to file mode: {e}")
                self.use_database = False
                self._db_initialized = False

        if not self.use_database:
            logger.info("Hybrid venue manager initialized in FILE mode")

    def find_venue_with_confidence(
        self,
        message: str,
        phone: str = None
    ) -> Tuple[Optional[Dict], float]:
        """
        Find venue from message with confidence scoring.
        Synchronous wrapper that handles both modes.
        """
        if self.use_database and self.db_manager:
            try:
                # Run async database query in sync context
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    venue, confidence = loop.run_until_complete(
                        self.db_manager.find_venue_with_confidence(message, phone)
                    )
                finally:
                    loop.close()

                # Convert database format to expected format
                if venue and confidence >= 0.9:
                    return self._convert_db_venue_to_dict(venue), confidence
                return None, 0.0

            except Exception as e:
                logger.error(f"Database venue lookup failed, falling back to file: {e}")
                # Fall back to file mode
                return self.file_manager.find_venue_with_confidence(message)
        else:
            # Use file-based manager
            return self.file_manager.find_venue_with_confidence(message)

    async def find_venue_with_confidence_async(
        self,
        message: str,
        phone: str = None
    ) -> Tuple[Optional[Dict], float]:
        """
        Async version for use in async contexts.
        """
        if self.use_database and self.db_manager:
            try:
                venue, confidence = await self.db_manager.find_venue_with_confidence(
                    message, phone
                )
                if venue and confidence >= 0.9:
                    return self._convert_db_venue_to_dict(venue), confidence
                return None, 0.0

            except Exception as e:
                logger.error(f"Database venue lookup failed: {e}")
                # Fall back to file mode (sync in async wrapper)
                return await asyncio.to_thread(
                    self.file_manager.find_venue_with_confidence, message
                )
        else:
            # Use file-based manager in thread
            return await asyncio.to_thread(
                self.file_manager.find_venue_with_confidence, message
            )

    def get_venue_info(self, venue_name: str) -> Optional[Dict]:
        """Get venue information by name"""
        if self.use_database and self.db_manager:
            try:
                # Search by name in database
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    venues = loop.run_until_complete(
                        self.db_manager.find_venues_by_name(venue_name, threshold=0.8, limit=1)
                    )
                finally:
                    loop.close()

                if venues:
                    return self._convert_db_venue_to_dict(venues[0])
                return None

            except Exception as e:
                logger.error(f"Database venue info lookup failed: {e}")
                return self.file_manager.get_venue_info(venue_name)
        else:
            return self.file_manager.get_venue_info(venue_name)

    async def get_venue_info_async(self, venue_name: str) -> Optional[Dict]:
        """Async version of get_venue_info"""
        if self.use_database and self.db_manager:
            try:
                venues = await self.db_manager.find_venues_by_name(
                    venue_name, threshold=0.8, limit=1
                )
                if venues:
                    return self._convert_db_venue_to_dict(venues[0])
                return None

            except Exception as e:
                logger.error(f"Database venue info lookup failed: {e}")
                return await asyncio.to_thread(
                    self.file_manager.get_venue_info, venue_name
                )
        else:
            return await asyncio.to_thread(
                self.file_manager.get_venue_info, venue_name
            )

    def find_possible_venues(
        self,
        message: str,
        threshold: float = 0.4
    ) -> List[Tuple[Dict, float]]:
        """Find possible venue matches"""
        if self.use_database and self.db_manager:
            try:
                # Get possible matches from database
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    venues = loop.run_until_complete(
                        self.db_manager.find_venues_by_name(message, threshold=threshold, limit=5)
                    )
                finally:
                    loop.close()

                # Convert to expected format
                results = []
                for venue in venues:
                    confidence = venue.get('match_score', 0.0)
                    venue_dict = self._convert_db_venue_to_dict(venue)
                    results.append((venue_dict, confidence))

                return results

            except Exception as e:
                logger.error(f"Database possible venues lookup failed: {e}")
                return self.file_manager.find_possible_venues(message, threshold)
        else:
            return self.file_manager.find_possible_venues(message, threshold)

    def _convert_db_venue_to_dict(self, db_venue: Dict) -> Dict:
        """Convert database venue format to expected dictionary format"""
        # Extract zone names from zones array
        zones = []
        if db_venue.get('zones'):
            if isinstance(db_venue['zones'], list):
                for zone in db_venue['zones']:
                    if isinstance(zone, dict):
                        zones.append(zone.get('name', ''))
                    else:
                        zones.append(str(zone))

        # Build venue dict in expected format
        venue_dict = {
            'name': db_venue.get('name', ''),
            'zones': zones,
            'platform': db_venue.get('platform'),
            'zone_count': db_venue.get('zone_count', len(zones)),
            'contract_end': db_venue.get('contract_end'),
            'annual_price': db_venue.get('annual_price_per_zone'),
            'hardware_type': db_venue.get('hardware_type'),
            'account_id': db_venue.get('soundtrack_account_id'),
            'contacts': []
        }

        # Add contacts if available
        if db_venue.get('contacts'):
            venue_dict['contacts'] = db_venue['contacts']

        return venue_dict

    def get_all_venues(self) -> Dict[str, Dict]:
        """Get all venues (primarily for testing/migration)"""
        if self.use_database and self.db_manager:
            logger.warning("get_all_venues not optimized for database mode")
            # This is expensive - should be avoided in production
            return {}
        else:
            return self.file_manager.venues

    async def health_check(self) -> Dict:
        """Check venue manager health"""
        health = {
            "mode": "database" if self.use_database else "file",
            "initialized": self._db_initialized if self.use_database else True,
            "venue_count": 0
        }

        if self.use_database and self.db_manager:
            try:
                db_health = await self.db_manager.health_check()
                health.update(db_health)
            except Exception as e:
                health["error"] = str(e)
        else:
            health["venue_count"] = len(self.file_manager.venues)

        return health

    def switch_mode(self, use_database: bool):
        """Switch between database and file mode (for testing)"""
        self.use_database = use_database
        self._db_initialized = False
        logger.info(f"Switched to {'database' if use_database else 'file'} mode")


# Create a singleton instance
_hybrid_manager: Optional[HybridVenueManager] = None


def get_hybrid_venue_manager() -> HybridVenueManager:
    """Get or create the hybrid venue manager singleton"""
    global _hybrid_manager

    if not _hybrid_manager:
        _hybrid_manager = HybridVenueManager()

    return _hybrid_manager


async def get_hybrid_venue_manager_async() -> HybridVenueManager:
    """Get or create and initialize the hybrid venue manager"""
    manager = get_hybrid_venue_manager()
    await manager.initialize()
    return manager