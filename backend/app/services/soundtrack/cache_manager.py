"""Cache management for API responses with Redis backend"""

import json
import hashlib
import asyncio
from typing import Optional, Any, Dict, List, Callable
from datetime import datetime, timedelta
import redis.asyncio as redis
from app.config import settings
import logging

logger = logging.getLogger(__name__)


class CacheManager:
    """
    Intelligent cache manager for API responses.
    Optimized for 10,000+ zones with tiered caching strategy.
    """
    
    def __init__(
        self,
        redis_client: Optional[redis.Redis] = None,
        default_ttl: int = 300,
        max_memory_items: int = 1000
    ):
        """
        Initialize cache manager.
        
        Args:
            redis_client: Redis client for distributed caching
            default_ttl: Default TTL in seconds
            max_memory_items: Maximum items in memory cache
        """
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.max_memory_items = max_memory_items
        
        # Multi-tier caching
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._cache_stats = {
            "hits": 0,
            "misses": 0,
            "memory_hits": 0,
            "redis_hits": 0,
            "evictions": 0
        }
        
        # Cache invalidation tracking
        self._invalidation_callbacks: Dict[str, List[Callable]] = {}
        
        # LRU tracking for memory cache
        self._access_times: Dict[str, datetime] = {}
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    async def initialize(self):
        """Initialize cache manager and connect to Redis if needed"""
        if not self.redis:
            try:
                self.redis = redis.from_url(
                    settings.redis_url,
                    decode_responses=True,
                    max_connections=50
                )
                await self.redis.ping()
                logger.info("Connected to Redis for caching")
            except Exception as e:
                logger.warning(f"Redis connection failed, using memory cache only: {e}")
                self.redis = None
    
    def _generate_key(self, namespace: str, identifier: str, params: Optional[Dict] = None) -> str:
        """Generate cache key from namespace, identifier and parameters"""
        key_parts = [namespace, identifier]
        
        if params:
            # Sort params for consistent key generation
            sorted_params = sorted(params.items())
            params_str = json.dumps(sorted_params, sort_keys=True)
            params_hash = hashlib.md5(params_str.encode()).hexdigest()[:8]
            key_parts.append(params_hash)
        
        return ":".join(key_parts)
    
    async def get(
        self,
        namespace: str,
        identifier: str,
        params: Optional[Dict] = None
    ) -> Optional[Any]:
        """
        Get item from cache.
        
        Args:
            namespace: Cache namespace (e.g., "zone_status")
            identifier: Item identifier (e.g., zone_id)
            params: Optional parameters for cache key
        
        Returns:
            Cached value or None if not found
        """
        key = self._generate_key(namespace, identifier, params)
        
        # Check memory cache first (L1)
        async with self._lock:
            if key in self._memory_cache:
                entry = self._memory_cache[key]
                if datetime.utcnow() < entry["expires_at"]:
                    self._cache_stats["hits"] += 1
                    self._cache_stats["memory_hits"] += 1
                    self._access_times[key] = datetime.utcnow()
                    return entry["value"]
                else:
                    # Expired, remove from memory
                    del self._memory_cache[key]
                    del self._access_times[key]
        
        # Check Redis cache (L2)
        if self.redis:
            try:
                value = await self.redis.get(key)
                if value:
                    self._cache_stats["hits"] += 1
                    self._cache_stats["redis_hits"] += 1
                    
                    # Deserialize
                    data = json.loads(value)
                    
                    # Add to memory cache for faster access
                    await self._add_to_memory_cache(key, data, ttl=60)
                    
                    return data
            except Exception as e:
                logger.error(f"Redis get error for key {key}: {e}")
        
        self._cache_stats["misses"] += 1
        return None
    
    async def set(
        self,
        namespace: str,
        identifier: str,
        value: Any,
        ttl: Optional[int] = None,
        params: Optional[Dict] = None
    ):
        """
        Set item in cache.
        
        Args:
            namespace: Cache namespace
            identifier: Item identifier
            value: Value to cache
            ttl: Time to live in seconds
            params: Optional parameters for cache key
        """
        key = self._generate_key(namespace, identifier, params)
        ttl = ttl or self.default_ttl
        
        # Add to memory cache
        await self._add_to_memory_cache(key, value, ttl)
        
        # Add to Redis cache
        if self.redis:
            try:
                serialized = json.dumps(value, default=str)
                await self.redis.setex(key, ttl, serialized)
            except Exception as e:
                logger.error(f"Redis set error for key {key}: {e}")
    
    async def _add_to_memory_cache(self, key: str, value: Any, ttl: int):
        """Add item to memory cache with LRU eviction"""
        async with self._lock:
            # Check if we need to evict items
            if len(self._memory_cache) >= self.max_memory_items:
                await self._evict_lru()
            
            self._memory_cache[key] = {
                "value": value,
                "expires_at": datetime.utcnow() + timedelta(seconds=ttl)
            }
            self._access_times[key] = datetime.utcnow()
    
    async def _evict_lru(self):
        """Evict least recently used items from memory cache"""
        if not self._access_times:
            return
        
        # Find LRU item
        lru_key = min(self._access_times, key=self._access_times.get)
        
        # Remove from caches
        if lru_key in self._memory_cache:
            del self._memory_cache[lru_key]
        if lru_key in self._access_times:
            del self._access_times[lru_key]
        
        self._cache_stats["evictions"] += 1
    
    async def delete(self, namespace: str, identifier: str, params: Optional[Dict] = None):
        """Delete item from cache"""
        key = self._generate_key(namespace, identifier, params)
        
        # Remove from memory cache
        async with self._lock:
            if key in self._memory_cache:
                del self._memory_cache[key]
            if key in self._access_times:
                del self._access_times[key]
        
        # Remove from Redis
        if self.redis:
            try:
                await self.redis.delete(key)
            except Exception as e:
                logger.error(f"Redis delete error for key {key}: {e}")
        
        # Trigger invalidation callbacks
        await self._trigger_invalidation_callbacks(key)
    
    async def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern"""
        # Clear matching keys from memory cache
        async with self._lock:
            keys_to_delete = [k for k in self._memory_cache if pattern in k]
            for key in keys_to_delete:
                del self._memory_cache[key]
                if key in self._access_times:
                    del self._access_times[key]
        
        # Clear from Redis
        if self.redis:
            try:
                cursor = 0
                while True:
                    cursor, keys = await self.redis.scan(cursor, match=f"*{pattern}*", count=100)
                    if keys:
                        await self.redis.delete(*keys)
                    if cursor == 0:
                        break
            except Exception as e:
                logger.error(f"Redis delete pattern error for {pattern}: {e}")
    
    async def get_or_set(
        self,
        namespace: str,
        identifier: str,
        factory: Callable,
        ttl: Optional[int] = None,
        params: Optional[Dict] = None
    ) -> Any:
        """
        Get from cache or compute and set if not found.
        
        Args:
            namespace: Cache namespace
            identifier: Item identifier
            factory: Async callable to compute value if not cached
            ttl: Time to live in seconds
            params: Optional parameters
        
        Returns:
            Cached or computed value
        """
        # Try to get from cache
        value = await self.get(namespace, identifier, params)
        if value is not None:
            return value
        
        # Compute value
        value = await factory()
        
        # Cache the result
        await self.set(namespace, identifier, value, ttl, params)
        
        return value
    
    async def batch_get(
        self,
        namespace: str,
        identifiers: List[str],
        params: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Get multiple items from cache.
        
        Args:
            namespace: Cache namespace
            identifiers: List of identifiers
            params: Optional parameters
        
        Returns:
            Dictionary of identifier -> value
        """
        results = {}
        
        # Check memory cache first
        async with self._lock:
            for identifier in identifiers:
                key = self._generate_key(namespace, identifier, params)
                if key in self._memory_cache:
                    entry = self._memory_cache[key]
                    if datetime.utcnow() < entry["expires_at"]:
                        results[identifier] = entry["value"]
                        self._access_times[key] = datetime.utcnow()
        
        # Get remaining from Redis
        missing = [id for id in identifiers if id not in results]
        if missing and self.redis:
            try:
                keys = [self._generate_key(namespace, id, params) for id in missing]
                values = await self.redis.mget(keys)
                
                for identifier, value in zip(missing, values):
                    if value:
                        data = json.loads(value)
                        results[identifier] = data
                        
                        # Add to memory cache
                        key = self._generate_key(namespace, identifier, params)
                        await self._add_to_memory_cache(key, data, ttl=60)
            except Exception as e:
                logger.error(f"Redis batch get error: {e}")
        
        return results
    
    async def batch_set(
        self,
        namespace: str,
        items: Dict[str, Any],
        ttl: Optional[int] = None,
        params: Optional[Dict] = None
    ):
        """
        Set multiple items in cache.
        
        Args:
            namespace: Cache namespace
            items: Dictionary of identifier -> value
            ttl: Time to live in seconds
            params: Optional parameters
        """
        ttl = ttl or self.default_ttl
        
        # Add to memory cache
        for identifier, value in items.items():
            key = self._generate_key(namespace, identifier, params)
            await self._add_to_memory_cache(key, value, ttl)
        
        # Add to Redis
        if self.redis:
            try:
                pipe = self.redis.pipeline()
                for identifier, value in items.items():
                    key = self._generate_key(namespace, identifier, params)
                    serialized = json.dumps(value, default=str)
                    pipe.setex(key, ttl, serialized)
                await pipe.execute()
            except Exception as e:
                logger.error(f"Redis batch set error: {e}")
    
    def add_invalidation_callback(self, pattern: str, callback: Callable):
        """Add callback to be triggered when cache keys matching pattern are invalidated"""
        if pattern not in self._invalidation_callbacks:
            self._invalidation_callbacks[pattern] = []
        self._invalidation_callbacks[pattern].append(callback)
    
    async def _trigger_invalidation_callbacks(self, key: str):
        """Trigger invalidation callbacks for a key"""
        for pattern, callbacks in self._invalidation_callbacks.items():
            if pattern in key:
                for callback in callbacks:
                    try:
                        await callback(key)
                    except Exception as e:
                        logger.error(f"Invalidation callback error: {e}")
    
    async def clear_expired(self):
        """Clear expired items from memory cache"""
        async with self._lock:
            now = datetime.utcnow()
            expired_keys = []
            
            for key, entry in self._memory_cache.items():
                if now >= entry["expires_at"]:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._memory_cache[key]
                if key in self._access_times:
                    del self._access_times[key]
            
            if expired_keys:
                logger.debug(f"Cleared {len(expired_keys)} expired items from memory cache")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        hit_rate = 0.0
        total = self._cache_stats["hits"] + self._cache_stats["misses"]
        if total > 0:
            hit_rate = (self._cache_stats["hits"] / total) * 100
        
        return {
            "hits": self._cache_stats["hits"],
            "misses": self._cache_stats["misses"],
            "hit_rate": hit_rate,
            "memory_hits": self._cache_stats["memory_hits"],
            "redis_hits": self._cache_stats["redis_hits"],
            "evictions": self._cache_stats["evictions"],
            "memory_cache_size": len(self._memory_cache),
            "redis_available": self.redis is not None
        }
    
    async def warmup(self, namespace: str, identifiers: List[str], factory: Callable, ttl: Optional[int] = None):
        """
        Warm up cache with pre-computed values.
        
        Args:
            namespace: Cache namespace
            identifiers: List of identifiers to warm up
            factory: Async callable that returns dict of identifier -> value
            ttl: Time to live in seconds
        """
        logger.info(f"Warming up cache for {len(identifiers)} items in namespace {namespace}")
        
        # Compute all values
        values = await factory(identifiers)
        
        # Batch set in cache
        await self.batch_set(namespace, values, ttl)
        
        logger.info(f"Cache warmup complete for namespace {namespace}")