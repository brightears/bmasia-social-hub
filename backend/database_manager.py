"""
High-performance database manager with connection pooling for PostgreSQL
Optimized for sub-10ms venue lookups and efficient bot queries
"""

import os
import json
import asyncio
import hashlib
import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from contextlib import asynccontextmanager
import asyncpg
from asyncpg import Pool, Connection
import redis.asyncio as redis

logger = logging.getLogger(__name__)

class DatabaseManager:
    """Async PostgreSQL database manager with connection pooling"""

    def __init__(self, database_url: str, redis_url: str = None):
        self.database_url = database_url
        self.redis_url = redis_url
        self.pool: Optional[Pool] = None
        self.redis_client: Optional[redis.Redis] = None
        self._initialized = False

    async def initialize(self):
        """Initialize database and Redis connections"""
        if self._initialized:
            return

        try:
            # Create PostgreSQL connection pool
            self.pool = await asyncpg.create_pool(
                self.database_url,
                min_size=5,
                max_size=20,
                max_queries=50000,
                max_inactive_connection_lifetime=300,
                command_timeout=30
            )
            logger.info("PostgreSQL connection pool created")

            # Initialize Redis if URL provided
            if self.redis_url:
                self.redis_client = redis.from_url(
                    self.redis_url,
                    encoding="utf-8",
                    decode_responses=True
                )
                await self.redis_client.ping()
                logger.info("Redis connection established")

            self._initialized = True

        except Exception as e:
            logger.error(f"Failed to initialize database manager: {e}")
            raise

    async def close(self):
        """Close all connections"""
        if self.pool:
            await self.pool.close()
        if self.redis_client:
            await self.redis_client.close()
        self._initialized = False

    @asynccontextmanager
    async def acquire(self):
        """Acquire a database connection from the pool"""
        async with self.pool.acquire() as connection:
            yield connection

    # ==================== Venue Queries ====================

    async def find_venues_by_name(
        self,
        search_text: str,
        threshold: float = 0.3,
        limit: int = 10
    ) -> List[Dict]:
        """
        Find venues by name with similarity scoring.
        Optimized for sub-10ms performance with caching.
        """
        # Try cache first
        cache_key = None
        if self.redis_client:
            cache_key = f"venue:search:{hashlib.md5(search_text.encode()).hexdigest()}"
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        # Database query with timeout
        try:
            async with asyncio.timeout(0.05):  # 50ms timeout
                async with self.acquire() as conn:
                    rows = await conn.fetch("""
                        WITH venue_matches AS (
                            SELECT
                                v.id,
                                v.name,
                                v.platform,
                                v.zone_count,
                                v.soundtrack_account_id,
                                v.contract_end,
                                v.hardware_type,
                                similarity(v.name, $1) as match_score
                            FROM venues v
                            WHERE v.is_active = TRUE
                                AND similarity(v.name, $1) > $2
                        )
                        SELECT
                            vm.*,
                            array_agg(
                                json_build_object(
                                    'name', z.name,
                                    'id', z.zone_id
                                ) ORDER BY z.zone_order
                            ) FILTER (WHERE z.id IS NOT NULL) as zones
                        FROM venue_matches vm
                        LEFT JOIN zones z ON vm.id = z.venue_id AND z.status = 'active'
                        GROUP BY vm.id, vm.name, vm.platform, vm.zone_count,
                                 vm.soundtrack_account_id, vm.contract_end,
                                 vm.hardware_type, vm.match_score
                        ORDER BY vm.match_score DESC, vm.zone_count DESC
                        LIMIT $3
                    """, search_text, threshold, limit)

                    results = [dict(row) for row in rows]

                    # Cache results for 5 minutes
                    if self.redis_client and results:
                        try:
                            await self.redis_client.setex(
                                cache_key,
                                300,
                                json.dumps(results, default=str)
                            )
                        except Exception as e:
                            logger.warning(f"Cache write failed: {e}")

                    return results

        except asyncio.TimeoutError:
            logger.warning(f"Venue search timeout for: {search_text}")
            return []
        except Exception as e:
            logger.error(f"Venue search failed: {e}")
            return []

    async def get_venue_by_id(self, venue_id: int) -> Optional[Dict]:
        """Get venue details by ID with caching"""
        # Try cache first
        cache_key = None
        if self.redis_client:
            cache_key = f"venue:id:{venue_id}"
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        try:
            async with self.acquire() as conn:
                row = await conn.fetchrow("""
                    SELECT
                        v.*,
                        array_agg(
                            json_build_object(
                                'name', z.name,
                                'id', z.zone_id,
                                'status', z.status
                            ) ORDER BY z.zone_order
                        ) FILTER (WHERE z.id IS NOT NULL) as zones,
                        array_agg(
                            json_build_object(
                                'role', c.role,
                                'name', c.name,
                                'email', c.email,
                                'phone', c.phone
                            ) ORDER BY c.is_primary DESC, c.role
                        ) FILTER (WHERE c.id IS NOT NULL) as contacts
                    FROM venues v
                    LEFT JOIN zones z ON v.id = z.venue_id
                    LEFT JOIN contacts c ON v.id = c.venue_id
                    WHERE v.id = $1 AND v.is_active = TRUE
                    GROUP BY v.id
                """, venue_id)

                if row:
                    result = dict(row)

                    # Cache for 1 hour
                    if self.redis_client:
                        try:
                            await self.redis_client.setex(
                                cache_key,
                                3600,
                                json.dumps(result, default=str)
                            )
                        except Exception as e:
                            logger.warning(f"Cache write failed: {e}")

                    return result

                return None

        except Exception as e:
            logger.error(f"Failed to get venue {venue_id}: {e}")
            return None

    async def find_venue_with_confidence(
        self,
        message: str,
        phone: str = None
    ) -> Tuple[Optional[Dict], float]:
        """
        Find venue from message with confidence scoring.
        Returns (venue_dict, confidence_score)
        """
        # Clean and prepare search text
        search_text = message.strip()

        # If message is too short, no point searching
        if len(search_text) < 3:
            return None, 0.0

        # Search for venues
        venues = await self.find_venues_by_name(search_text, threshold=0.3, limit=5)

        if not venues:
            return None, 0.0

        # Get the best match
        best_match = venues[0]
        confidence = best_match.get('match_score', 0.0)

        # Only return venue if confidence is high enough (90%+)
        if confidence >= 0.9:
            return best_match, confidence

        return None, 0.0

    # ==================== Product Info Queries ====================

    async def get_product_info(
        self,
        product_names: List[str] = None,
        category: str = None
    ) -> List[Dict]:
        """Get product information with caching"""
        # Build cache key
        cache_key = None
        if self.redis_client:
            key_parts = product_names or ['all']
            if category:
                key_parts.append(category)
            cache_key = f"product:{':'.join(key_parts)}"

            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        try:
            async with self.acquire() as conn:
                if product_names and category:
                    rows = await conn.fetch("""
                        SELECT product_name, category, key, value
                        FROM product_info
                        WHERE is_active = TRUE
                            AND product_name = ANY($1::text[])
                            AND category = $2
                        ORDER BY product_name, key
                    """, product_names, category)
                elif product_names:
                    rows = await conn.fetch("""
                        SELECT product_name, category, key, value
                        FROM product_info
                        WHERE is_active = TRUE
                            AND product_name = ANY($1::text[])
                        ORDER BY product_name, category, key
                    """, product_names)
                else:
                    rows = await conn.fetch("""
                        SELECT product_name, category, key, value
                        FROM product_info
                        WHERE is_active = TRUE
                        ORDER BY product_name, category, key
                    """)

                results = [dict(row) for row in rows]

                # Cache for 24 hours (product info rarely changes)
                if self.redis_client and results:
                    try:
                        await self.redis_client.setex(
                            cache_key,
                            86400,
                            json.dumps(results, default=str)
                        )
                    except Exception as e:
                        logger.warning(f"Cache write failed: {e}")

                return results

        except Exception as e:
            logger.error(f"Failed to get product info: {e}")
            return []

    # ==================== Conversation Management ====================

    async def create_conversation(
        self,
        customer_phone: str,
        customer_name: str = None,
        venue_id: int = None,
        platform: str = "WhatsApp",
        thread_key: str = None
    ) -> str:
        """Create a new conversation and return the conversation ID"""
        try:
            async with self.acquire() as conn:
                row = await conn.fetchrow("""
                    INSERT INTO conversations (
                        customer_phone, customer_name, venue_id,
                        platform, thread_key, status, mode
                    )
                    VALUES ($1, $2, $3, $4, $5, 'active', 'bot')
                    RETURNING id::text
                """, customer_phone, customer_name, venue_id, platform, thread_key)

                return row['id']

        except Exception as e:
            logger.error(f"Failed to create conversation: {e}")
            return None

    async def get_conversation_by_phone(
        self,
        phone: str,
        platform: str = None,
        hours: int = 24
    ) -> Optional[Dict]:
        """Get active conversation for a phone number"""
        try:
            async with self.acquire() as conn:
                if platform:
                    row = await conn.fetchrow("""
                        SELECT * FROM conversations
                        WHERE customer_phone = $1
                            AND platform = $2
                            AND status = 'active'
                            AND last_message_at > NOW() - INTERVAL '%s hours'
                        ORDER BY last_message_at DESC
                        LIMIT 1
                    """ % hours, phone, platform)
                else:
                    row = await conn.fetchrow("""
                        SELECT * FROM conversations
                        WHERE customer_phone = $1
                            AND status = 'active'
                            AND last_message_at > NOW() - INTERVAL '%s hours'
                        ORDER BY last_message_at DESC
                        LIMIT 1
                    """ % hours, phone)

                return dict(row) if row else None

        except Exception as e:
            logger.error(f"Failed to get conversation: {e}")
            return None

    async def add_message(
        self,
        conversation_id: str,
        content: str,
        sender_type: str,
        sender_id: str = None,
        message_type: str = 'text',
        metadata: Dict = None
    ):
        """Add a message to a conversation"""
        try:
            async with self.acquire() as conn:
                # Add message
                await conn.execute("""
                    INSERT INTO messages (
                        conversation_id, sender_type, sender_id,
                        content, message_type, metadata
                    )
                    VALUES ($1, $2, $3, $4, $5, $6)
                """, conversation_id, sender_type, sender_id, content,
                    message_type, json.dumps(metadata) if metadata else None)

                # Update conversation last_message_at
                await conn.execute("""
                    UPDATE conversations
                    SET last_message_at = NOW()
                    WHERE id = $1::uuid
                """, conversation_id)

        except Exception as e:
            logger.error(f"Failed to add message: {e}")

    async def get_conversation_context(
        self,
        phone: str,
        limit: int = 10
    ) -> List[Dict]:
        """Get recent conversation messages for context"""
        # Try cache first
        cache_key = None
        if self.redis_client:
            cache_key = f"context:{phone}"
            try:
                cached = await self.redis_client.get(cache_key)
                if cached:
                    return json.loads(cached)
            except Exception as e:
                logger.warning(f"Cache read failed: {e}")

        try:
            async with self.acquire() as conn:
                rows = await conn.fetch("""
                    SELECT m.sender_type, m.content, m.created_at
                    FROM messages m
                    JOIN conversations c ON m.conversation_id = c.id
                    WHERE c.customer_phone = $1
                        AND c.status = 'active'
                        AND m.created_at > NOW() - INTERVAL '24 hours'
                    ORDER BY m.created_at DESC
                    LIMIT $2
                """, phone, limit)

                # Convert to context format
                context = []
                for row in reversed(rows):  # Reverse to get chronological order
                    role = "user" if row['sender_type'] == 'customer' else "assistant"
                    context.append({
                        "role": role,
                        "content": row['content']
                    })

                # Cache for 30 minutes
                if self.redis_client and context:
                    try:
                        await self.redis_client.setex(
                            cache_key,
                            1800,
                            json.dumps(context)
                        )
                    except Exception as e:
                        logger.warning(f"Cache write failed: {e}")

                return context

        except Exception as e:
            logger.error(f"Failed to get conversation context: {e}")
            return []

    # ==================== Cache Management ====================

    async def warm_cache(self, top_venues: int = 100):
        """Pre-load frequently accessed venues into cache"""
        if not self.redis_client:
            return

        try:
            async with self.acquire() as conn:
                # Get most active venues
                rows = await conn.fetch("""
                    SELECT v.*, COUNT(c.id) as conversation_count
                    FROM venues v
                    LEFT JOIN conversations c ON v.id = c.venue_id
                        AND c.created_at > NOW() - INTERVAL '30 days'
                    WHERE v.is_active = TRUE
                    GROUP BY v.id
                    ORDER BY conversation_count DESC
                    LIMIT $1
                """, top_venues)

                # Cache each venue
                pipeline = self.redis_client.pipeline()
                for row in rows:
                    venue_data = dict(row)
                    cache_key = f"venue:id:{venue_data['id']}"
                    pipeline.setex(
                        cache_key,
                        3600,
                        json.dumps(venue_data, default=str)
                    )

                await pipeline.execute()
                logger.info(f"Warmed cache with {len(rows)} venues")

        except Exception as e:
            logger.error(f"Failed to warm cache: {e}")

    async def clear_cache(self, pattern: str = None):
        """Clear cache entries matching pattern"""
        if not self.redis_client:
            return

        try:
            if pattern:
                cursor = 0
                while True:
                    cursor, keys = await self.redis_client.scan(
                        cursor, match=pattern, count=100
                    )
                    if keys:
                        await self.redis_client.delete(*keys)
                    if cursor == 0:
                        break
            else:
                await self.redis_client.flushdb()

            logger.info(f"Cleared cache: {pattern or 'all'}")

        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")

    # ==================== Health & Stats ====================

    async def health_check(self) -> Dict[str, Any]:
        """Check database and cache health"""
        health = {
            "database": False,
            "cache": False,
            "pool_size": 0,
            "pool_free": 0
        }

        try:
            # Check database
            async with self.acquire() as conn:
                await conn.fetchval("SELECT 1")
                health["database"] = True

            # Get pool stats
            if self.pool:
                health["pool_size"] = self.pool.get_size()
                health["pool_free"] = self.pool.get_idle_size()

            # Check cache
            if self.redis_client:
                await self.redis_client.ping()
                health["cache"] = True

        except Exception as e:
            logger.error(f"Health check failed: {e}")

        return health


# Singleton instance
_db_manager: Optional[DatabaseManager] = None


async def get_database_manager() -> DatabaseManager:
    """Get or create the database manager singleton"""
    global _db_manager

    if not _db_manager:
        database_url = os.getenv('DATABASE_URL')
        redis_url = os.getenv('REDIS_URL')

        if not database_url:
            raise ValueError("DATABASE_URL not configured")

        _db_manager = DatabaseManager(database_url, redis_url)
        await _db_manager.initialize()

    return _db_manager