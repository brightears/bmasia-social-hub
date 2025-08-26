"""
Redis cache management for high-performance operations.
Optimized for 10,000+ zones with intelligent caching strategies.
"""

import asyncio
import json
import logging
import hashlib
import pickle
from typing import Any, Dict, List, Optional, Union, Callable
from datetime import datetime, timedelta
import random

import redis.asyncio as redis
from redis.asyncio import ConnectionPool
from redis.exceptions import RedisError

from app.config import settings

logger = logging.getLogger(__name__)


class CacheKeyBuilder:
    """Build consistent cache keys"""
    
    @staticmethod
    def venue_status(venue_id: str) -> str:
        return f"venue:status:{venue_id}"
    
    @staticmethod
    def zone_status(zone_id: str) -> str:
        return f"zone:status:{zone_id}"
    
    @staticmethod
    def conversation_session(conversation_id: str) -> str:
        return f"conversation:session:{conversation_id}"
    
    @staticmethod
    def user_session(user_id: str) -> str:
        return f"user:session:{user_id}"
    
    @staticmethod
    def api_response(endpoint: str, params: Dict) -> str:
        """Generate cache key for API responses"""
        param_str = json.dumps(params, sort_keys=True)
        hash_key = hashlib.md5(param_str.encode()).hexdigest()
        return f"api:{endpoint}:{hash_key}"
    
    @staticmethod
    def monitoring_batch(batch_id: str) -> str:
        return f"monitoring:batch:{batch_id}"
    
    @staticmethod
    def rate_limit(identifier: str, window: str) -> str:
        return f"ratelimit:{window}:{identifier}"
    
    @staticmethod
    def lock(resource: str) -> str:
        return f"lock:{resource}"


class RedisManager:
    """
    Redis manager with advanced caching patterns for BMA Social.
    Supports cache-aside, write-through, and write-behind patterns.
    """
    
    def __init__(self):
        self.pool: Optional[ConnectionPool] = None
        self.redis: Optional[redis.Redis] = None
        self.pubsub: Optional[redis.client.PubSub] = None
        
        # Default TTLs for different data types (seconds)
        self.default_ttls = {
            "zone_status": 60,  # 1 minute
            "venue_config": 3600,  # 1 hour
            "api_response": 300,  # 5 minutes
            "session": 1800,  # 30 minutes
            "monitoring": 300,  # 5 minutes
            "conversation": 86400,  # 24 hours
        }
        
        # Cache statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "errors": 0,
        }
    
    async def initialize(self):
        """Initialize Redis connection pool"""
        logger.info("Starting Redis initialization...")
        
        try:
            # Parse Redis URL
            logger.info(f"Connecting to Redis: {settings.redis_url.split('@')[1] if '@' in settings.redis_url else 'local'}")
            
            self.pool = ConnectionPool.from_url(
                settings.redis_url,
                max_connections=settings.redis_max_connections,
                decode_responses=settings.redis_decode_responses,
                socket_keepalive=True,
                socket_keepalive_options={
                    1: 1,  # TCP_KEEPIDLE
                    2: 2,  # TCP_KEEPINTVL  
                    3: 3,  # TCP_KEEPCNT
                },
                retry_on_timeout=True,
                retry_on_error=[ConnectionError, TimeoutError],
                socket_connect_timeout=5,  # 5 second connection timeout
                socket_timeout=5,  # 5 second socket timeout
            )
            
            self.redis = redis.Redis(connection_pool=self.pool)
            
            # Test connection with timeout
            import asyncio
            await asyncio.wait_for(self.redis.ping(), timeout=5.0)
            
            # Initialize pub/sub
            self.pubsub = self.redis.pubsub()
            
            logger.info("Redis initialized successfully")
            
        except asyncio.TimeoutError:
            logger.error("Redis ping timed out after 5 seconds")
            # Don't raise - allow app to start without Redis
            self.redis = None
            self.pool = None
        except Exception as e:
            logger.error(f"Failed to initialize Redis: {e}")
            # Don't raise - allow app to start without Redis
            self.redis = None
            self.pool = None
    
    async def close(self):
        """Close Redis connections"""
        if self.pubsub:
            await self.pubsub.close()
        if self.redis:
            await self.redis.close()
        if self.pool:
            await self.pool.disconnect()
    
    # Basic Operations
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.redis:
            self._stats["errors"] += 1
            return None
            
        try:
            value = await self.redis.get(key)
            if value:
                self._stats["hits"] += 1
            else:
                self._stats["misses"] += 1
            return value
        except (RedisError, AttributeError) as e:
            self._stats["errors"] += 1
            logger.error(f"Redis GET error for key {key}: {e}")
            return None
    
    async def set(self, key: str, value: Union[str, Dict, List], ttl: Optional[int] = None) -> bool:
        """Set value in cache"""
        if not self.redis:
            self._stats["errors"] += 1
            return False
            
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
            
            if ttl:
                await self.redis.setex(key, ttl, value)
            else:
                await self.redis.set(key, value)
            
            return True
        except (RedisError, AttributeError) as e:
            self._stats["errors"] += 1
            logger.error(f"Redis SET error for key {key}: {e}")
            return False
    
    async def setex(self, key: str, ttl: int, value: Union[str, Dict, List]) -> bool:
        """Set value with expiration"""
        return await self.set(key, value, ttl)
    
    async def delete(self, *keys: str) -> int:
        """Delete keys from cache"""
        try:
            return await self.redis.delete(*keys)
        except RedisError as e:
            logger.error(f"Redis DELETE error: {e}")
            return 0
    
    async def exists(self, key: str) -> bool:
        """Check if key exists"""
        try:
            return await self.redis.exists(key) > 0
        except RedisError:
            return False
    
    # Advanced Patterns
    
    async def get_or_set(
        self,
        key: str,
        fetch_func: Callable,
        ttl: Optional[int] = None,
        use_lock: bool = True
    ) -> Any:
        """
        Cache-aside pattern with stampede protection.
        Gets from cache or fetches and caches if missing.
        """
        # Try to get from cache
        cached = await self.get(key)
        if cached:
            try:
                return json.loads(cached) if cached.startswith('{') or cached.startswith('[') else cached
            except json.JSONDecodeError:
                return cached
        
        # Use distributed lock to prevent stampede
        if use_lock:
            lock_key = CacheKeyBuilder.lock(key)
            lock_acquired = await self.acquire_lock(lock_key, timeout=10)
            
            if lock_acquired:
                try:
                    # Double-check cache after acquiring lock
                    cached = await self.get(key)
                    if cached:
                        try:
                            return json.loads(cached) if cached.startswith('{') or cached.startswith('[') else cached
                        except json.JSONDecodeError:
                            return cached
                    
                    # Fetch fresh data
                    data = await fetch_func()
                    
                    # Store in cache
                    await self.set(key, data, ttl)
                    
                    return data
                finally:
                    await self.release_lock(lock_key)
            else:
                # Wait for lock holder to populate cache
                for _ in range(20):  # Max 2 seconds wait
                    await asyncio.sleep(0.1)
                    cached = await self.get(key)
                    if cached:
                        try:
                            return json.loads(cached) if cached.startswith('{') or cached.startswith('[') else cached
                        except json.JSONDecodeError:
                            return cached
                
                # Fallback: fetch directly without caching
                return await fetch_func()
        else:
            # Fetch without lock (for non-critical data)
            data = await fetch_func()
            await self.set(key, data, ttl)
            return data
    
    async def write_through(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Write-through cache pattern - write to cache and notify subscribers"""
        success = await self.set(key, value, ttl)
        
        if success:
            # Publish invalidation event
            await self.redis.publish(f"cache:invalidate:{key}", "updated")
        
        return success
    
    async def invalidate_pattern(self, pattern: str) -> int:
        """Invalidate all keys matching a pattern"""
        try:
            cursor = b'0'
            count = 0
            
            while cursor:
                cursor, keys = await self.redis.scan(
                    cursor,
                    match=pattern,
                    count=100
                )
                
                if keys:
                    count += await self.redis.delete(*keys)
                
                if cursor == b'0':
                    break
            
            return count
        except RedisError as e:
            logger.error(f"Redis pattern invalidation error: {e}")
            return 0
    
    # Batch Operations
    
    async def mget(self, keys: List[str]) -> Dict[str, Optional[str]]:
        """Get multiple keys at once"""
        try:
            values = await self.redis.mget(keys)
            return dict(zip(keys, values))
        except RedisError as e:
            logger.error(f"Redis MGET error: {e}")
            return {key: None for key in keys}
    
    async def mset(self, mapping: Dict[str, Union[str, Dict, List]]) -> bool:
        """Set multiple keys at once"""
        try:
            processed = {}
            for key, value in mapping.items():
                if isinstance(value, (dict, list)):
                    processed[key] = json.dumps(value)
                else:
                    processed[key] = value
            
            await self.redis.mset(processed)
            return True
        except RedisError as e:
            logger.error(f"Redis MSET error: {e}")
            return False
    
    async def pipeline_execute(self, commands: List[tuple]) -> List[Any]:
        """Execute multiple commands in a pipeline"""
        try:
            async with self.redis.pipeline() as pipe:
                for cmd, *args in commands:
                    getattr(pipe, cmd)(*args)
                
                return await pipe.execute()
        except RedisError as e:
            logger.error(f"Redis pipeline error: {e}")
            return []
    
    # Zone Status Caching
    
    async def cache_zone_statuses(self, zone_statuses: Dict[str, Dict]) -> bool:
        """Bulk cache zone statuses efficiently"""
        try:
            pipeline = self.redis.pipeline()
            
            for zone_id, status in zone_statuses.items():
                key = CacheKeyBuilder.zone_status(zone_id)
                pipeline.setex(key, self.default_ttls["zone_status"], json.dumps(status))
            
            await pipeline.execute()
            return True
        except RedisError as e:
            logger.error(f"Failed to cache zone statuses: {e}")
            return False
    
    async def get_zone_statuses(self, zone_ids: List[str]) -> Dict[str, Optional[Dict]]:
        """Get multiple zone statuses from cache"""
        keys = [CacheKeyBuilder.zone_status(zone_id) for zone_id in zone_ids]
        cached = await self.mget(keys)
        
        result = {}
        for zone_id, key in zip(zone_ids, keys):
            value = cached.get(key)
            if value:
                try:
                    result[zone_id] = json.loads(value)
                except json.JSONDecodeError:
                    result[zone_id] = None
            else:
                result[zone_id] = None
        
        return result
    
    # Distributed Locking
    
    async def acquire_lock(
        self,
        lock_key: str,
        timeout: int = 10,
        retry_delay: float = 0.1
    ) -> bool:
        """Acquire a distributed lock"""
        identifier = str(random.random())
        end = asyncio.get_event_loop().time() + timeout
        
        while asyncio.get_event_loop().time() < end:
            if await self.redis.set(lock_key, identifier, nx=True, ex=timeout):
                return True
            
            await asyncio.sleep(retry_delay)
        
        return False
    
    async def release_lock(self, lock_key: str) -> bool:
        """Release a distributed lock"""
        try:
            await self.redis.delete(lock_key)
            return True
        except RedisError:
            return False
    
    # Rate Limiting
    
    async def check_rate_limit(
        self,
        identifier: str,
        limit: int,
        window: int
    ) -> tuple[bool, int]:
        """
        Check rate limit using sliding window.
        Returns (allowed, remaining_calls)
        """
        key = CacheKeyBuilder.rate_limit(identifier, str(window))
        
        try:
            pipeline = self.redis.pipeline()
            now = int(datetime.utcnow().timestamp())
            
            # Remove old entries
            pipeline.zremrangebyscore(key, 0, now - window)
            
            # Count current entries
            pipeline.zcard(key)
            
            # Add current request
            pipeline.zadd(key, {str(now): now})
            
            # Set expiry
            pipeline.expire(key, window)
            
            results = await pipeline.execute()
            current_count = results[1]
            
            if current_count < limit:
                return True, limit - current_count - 1
            else:
                # Remove the request we just added
                await self.redis.zrem(key, str(now))
                return False, 0
                
        except RedisError as e:
            logger.error(f"Rate limit check error: {e}")
            return True, limit  # Allow on error
    
    # Pub/Sub
    
    async def publish(self, channel: str, message: Union[str, Dict]) -> int:
        """Publish message to channel"""
        try:
            if isinstance(message, dict):
                message = json.dumps(message)
            
            return await self.redis.publish(channel, message)
        except RedisError as e:
            logger.error(f"Redis publish error: {e}")
            return 0
    
    async def subscribe(self, *channels: str) -> None:
        """Subscribe to channels"""
        if self.pubsub:
            await self.pubsub.subscribe(*channels)
    
    async def get_message(self, timeout: float = 1.0) -> Optional[Dict]:
        """Get message from subscribed channels"""
        if self.pubsub:
            return await self.pubsub.get_message(timeout=timeout)
        return None
    
    # Health & Metrics
    
    async def health_check(self) -> Dict[str, Any]:
        """Check Redis health"""
        if not self.redis:
            return {
                "status": "not_initialized",
                "error": "Redis client not initialized",
                "stats": self._stats.copy(),
            }
            
        try:
            start = asyncio.get_event_loop().time()
            await self.redis.ping()
            latency = (asyncio.get_event_loop().time() - start) * 1000
            
            info = await self.redis.info()
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "connected_clients": info.get("connected_clients"),
                "used_memory_human": info.get("used_memory_human"),
                "cache_hit_rate": self.get_hit_rate(),
                "stats": self._stats.copy(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "stats": self._stats.copy(),
            }
    
    def get_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self._stats["hits"] + self._stats["misses"]
        if total == 0:
            return 0.0
        return (self._stats["hits"] / total) * 100


# Create global Redis manager instance
redis_manager = RedisManager()