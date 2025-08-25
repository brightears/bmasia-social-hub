"""
Soundtrack Your Brand API Client
Optimized for 10,000+ zones with connection pooling and resilience patterns
"""

import asyncio
import time
import logging
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
from enum import Enum
import hashlib
import json

import aiohttp
import backoff
from aiohttp import ClientError, ClientTimeout, TCPConnector

from app.config import settings
from app.core.redis import redis_manager

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


@dataclass
class RateLimitConfig:
    """Rate limiting configuration"""
    requests_per_minute: int = 1000
    requests_per_second: int = 50
    burst_size: int = 100


class CircuitBreaker:
    """Circuit breaker pattern implementation"""
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = ClientError
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = CircuitBreakerState.CLOSED
    
    async def call(self, func, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        if self.state == CircuitBreakerState.OPEN:
            if self._should_attempt_reset():
                self.state = CircuitBreakerState.HALF_OPEN
            else:
                raise Exception("Circuit breaker is OPEN")
        
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exception as e:
            self._on_failure()
            raise e
    
    def _should_attempt_reset(self) -> bool:
        """Check if we should try to reset the circuit"""
        return (
            self.last_failure_time and
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self):
        """Handle successful call"""
        self.failure_count = 0
        self.state = CircuitBreakerState.CLOSED
    
    def _on_failure(self):
        """Handle failed call"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = CircuitBreakerState.OPEN
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class TokenBucketRateLimiter:
    """Token bucket algorithm for rate limiting"""
    
    def __init__(self, config: RateLimitConfig):
        self.config = config
        self.tokens = config.burst_size
        self.last_refill = time.time()
        self.lock = asyncio.Lock()
    
    async def acquire(self, tokens: int = 1) -> bool:
        """Acquire tokens for request"""
        async with self.lock:
            await self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            # Calculate wait time
            tokens_needed = tokens - self.tokens
            wait_time = tokens_needed / self.config.requests_per_second
            
            if wait_time > 10:  # Max 10 second wait
                return False
            
            await asyncio.sleep(wait_time)
            await self._refill()
            
            if self.tokens >= tokens:
                self.tokens -= tokens
                return True
            
            return False
    
    async def _refill(self):
        """Refill tokens based on time passed"""
        now = time.time()
        time_passed = now - self.last_refill
        
        new_tokens = time_passed * (self.config.requests_per_second)
        self.tokens = min(self.config.burst_size, self.tokens + new_tokens)
        self.last_refill = now


class SoundtrackClient:
    """
    Soundtrack Your Brand API client with production-grade features:
    - Connection pooling for 10,000+ zones
    - Rate limiting (1000 req/min)
    - Circuit breaker pattern
    - Exponential backoff retry
    - Response caching
    - Batch operations
    """
    
    def __init__(self):
        self.base_url = settings.soundtrack_base_url
        self.client_id = settings.soundtrack_client_id
        self.client_secret = settings.soundtrack_client_secret
        
        self.session: Optional[aiohttp.ClientSession] = None
        self.access_token: Optional[str] = None
        self.token_expires_at: Optional[datetime] = None
        
        self.rate_limiter = TokenBucketRateLimiter(RateLimitConfig())
        self.circuit_breaker = CircuitBreaker()
        
        # Semaphore for concurrent requests
        self._request_semaphore = asyncio.Semaphore(50)
        
        # Cache settings
        self.cache_ttl = {
            "device_status": 60,  # 1 minute
            "device_info": 300,  # 5 minutes
            "playlists": 3600,  # 1 hour
            "locations": 3600,  # 1 hour
        }
    
    async def initialize(self):
        """Initialize HTTP session with connection pooling"""
        connector = TCPConnector(
            limit=settings.soundtrack_max_connections,
            limit_per_host=30,
            ttl_dns_cache=300,
            keepalive_timeout=30,
            force_close=False,
            enable_cleanup_closed=True,
        )
        
        timeout = ClientTimeout(
            total=30,
            connect=5,
            sock_connect=5,
            sock_read=25,
        )
        
        self.session = aiohttp.ClientSession(
            connector=connector,
            timeout=timeout,
            headers={
                "User-Agent": "BMA-Social/2.0",
                "Accept": "application/json",
            },
        )
        
        # Get initial access token
        await self._ensure_authenticated()
        
        logger.info("Soundtrack API client initialized")
    
    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()
    
    async def _ensure_authenticated(self):
        """Ensure we have a valid access token"""
        if not self.access_token or not self._is_token_valid():
            await self._authenticate()
    
    def _is_token_valid(self) -> bool:
        """Check if current token is still valid"""
        if not self.token_expires_at:
            return False
        
        # Refresh 5 minutes before expiry
        buffer = timedelta(minutes=5)
        return datetime.utcnow() < (self.token_expires_at - buffer)
    
    async def _authenticate(self):
        """Authenticate with OAuth 2.0"""
        auth_url = f"{self.base_url}/oauth/token"
        
        data = {
            "grant_type": "client_credentials",
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "scope": "devices playlists control",
        }
        
        async with self.session.post(auth_url, data=data) as response:
            response.raise_for_status()
            result = await response.json()
            
            self.access_token = result["access_token"]
            expires_in = result.get("expires_in", 3600)
            self.token_expires_at = datetime.utcnow() + timedelta(seconds=expires_in)
            
            logger.info("Successfully authenticated with Soundtrack API")
    
    @backoff.on_exception(
        backoff.expo,
        ClientError,
        max_tries=3,
        max_time=10,
    )
    async def _make_request(
        self,
        method: str,
        endpoint: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Make authenticated API request with retry logic"""
        await self._ensure_authenticated()
        
        # Rate limiting
        if not await self.rate_limiter.acquire():
            raise Exception("Rate limit exceeded")
        
        # Build full URL
        url = f"{self.base_url}{endpoint}"
        
        # Add auth header
        headers = kwargs.pop("headers", {})
        headers["Authorization"] = f"Bearer {self.access_token}"
        
        # Execute with circuit breaker
        async with self._request_semaphore:
            return await self.circuit_breaker.call(
                self._execute_request,
                method,
                url,
                headers=headers,
                **kwargs
            )
    
    async def _execute_request(
        self,
        method: str,
        url: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute HTTP request"""
        async with self.session.request(method, url, **kwargs) as response:
            response.raise_for_status()
            return await response.json()
    
    # Device/Zone Operations
    
    async def get_device(self, device_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get device information"""
        cache_key = f"soundtrack:device:{device_id}"
        
        if use_cache:
            cached = await redis_manager.get(cache_key)
            if cached:
                return json.loads(cached)
        
        result = await self._make_request("GET", f"/devices/{device_id}")
        
        # Cache result
        await redis_manager.setex(
            cache_key,
            self.cache_ttl["device_info"],
            json.dumps(result)
        )
        
        return result
    
    async def get_device_status(self, device_id: str, use_cache: bool = True) -> Dict[str, Any]:
        """Get current device status"""
        cache_key = f"soundtrack:status:{device_id}"
        
        if use_cache:
            cached = await redis_manager.get(cache_key)
            if cached:
                return json.loads(cached)
        
        result = await self._make_request("GET", f"/devices/{device_id}/status")
        
        # Cache for short duration
        await redis_manager.setex(
            cache_key,
            self.cache_ttl["device_status"],
            json.dumps(result)
        )
        
        return result
    
    async def batch_get_device_status(
        self,
        device_ids: List[str],
        batch_size: int = 50
    ) -> List[Dict[str, Any]]:
        """Get status for multiple devices in batches"""
        results = []
        
        for i in range(0, len(device_ids), batch_size):
            batch = device_ids[i:i + batch_size]
            
            # Create tasks for parallel execution
            tasks = [
                self.get_device_status(device_id)
                for device_id in batch
            ]
            
            # Execute batch with error handling
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            # Process results
            for device_id, result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to get status for device {device_id}: {result}")
                    results.append({
                        "device_id": device_id,
                        "status": "error",
                        "error": str(result)
                    })
                else:
                    results.append(result)
        
        return results
    
    # Control Operations
    
    async def set_volume(self, device_id: str, volume: int) -> Dict[str, Any]:
        """Set device volume (0-100)"""
        if not 0 <= volume <= 100:
            raise ValueError("Volume must be between 0 and 100")
        
        data = {"volume": volume}
        
        result = await self._make_request(
            "POST",
            f"/devices/{device_id}/volume",
            json=data
        )
        
        # Invalidate status cache
        await redis_manager.delete(f"soundtrack:status:{device_id}")
        
        return result
    
    async def batch_set_volume(
        self,
        volume_changes: List[Tuple[str, int]],
        batch_size: int = 20
    ) -> List[Dict[str, Any]]:
        """Set volume for multiple devices"""
        results = []
        
        for i in range(0, len(volume_changes), batch_size):
            batch = volume_changes[i:i + batch_size]
            
            tasks = [
                self.set_volume(device_id, volume)
                for device_id, volume in batch
            ]
            
            batch_results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for (device_id, volume), result in zip(batch, batch_results):
                if isinstance(result, Exception):
                    logger.error(f"Failed to set volume for device {device_id}: {result}")
                    results.append({
                        "device_id": device_id,
                        "success": False,
                        "error": str(result)
                    })
                else:
                    results.append({
                        "device_id": device_id,
                        "success": True,
                        "volume": volume
                    })
        
        return results
    
    async def set_playlist(self, device_id: str, playlist_id: str) -> Dict[str, Any]:
        """Change device playlist"""
        data = {"playlist_id": playlist_id}
        
        result = await self._make_request(
            "POST",
            f"/devices/{device_id}/playlist",
            json=data
        )
        
        # Invalidate cache
        await redis_manager.delete(f"soundtrack:status:{device_id}")
        
        return result
    
    async def play(self, device_id: str) -> Dict[str, Any]:
        """Start playback on device"""
        result = await self._make_request(
            "POST",
            f"/devices/{device_id}/play"
        )
        
        await redis_manager.delete(f"soundtrack:status:{device_id}")
        return result
    
    async def pause(self, device_id: str) -> Dict[str, Any]:
        """Pause playback on device"""
        result = await self._make_request(
            "POST",
            f"/devices/{device_id}/pause"
        )
        
        await redis_manager.delete(f"soundtrack:status:{device_id}")
        return result
    
    async def skip(self, device_id: str) -> Dict[str, Any]:
        """Skip to next track"""
        result = await self._make_request(
            "POST",
            f"/devices/{device_id}/skip"
        )
        
        await redis_manager.delete(f"soundtrack:status:{device_id}")
        return result
    
    # Playlist Operations
    
    async def get_playlists(self, location_id: Optional[str] = None) -> List[Dict[str, Any]]:
        """Get available playlists"""
        cache_key = f"soundtrack:playlists:{location_id or 'all'}"
        
        cached = await redis_manager.get(cache_key)
        if cached:
            return json.loads(cached)
        
        params = {}
        if location_id:
            params["location_id"] = location_id
        
        result = await self._make_request("GET", "/playlists", params=params)
        
        await redis_manager.setex(
            cache_key,
            self.cache_ttl["playlists"],
            json.dumps(result)
        )
        
        return result
    
    async def get_playlist(self, playlist_id: str) -> Dict[str, Any]:
        """Get specific playlist details"""
        cache_key = f"soundtrack:playlist:{playlist_id}"
        
        cached = await redis_manager.get(cache_key)
        if cached:
            return json.loads(cached)
        
        result = await self._make_request("GET", f"/playlists/{playlist_id}")
        
        await redis_manager.setex(
            cache_key,
            self.cache_ttl["playlists"],
            json.dumps(result)
        )
        
        return result
    
    # Monitoring & Health
    
    async def health_check(self) -> Dict[str, Any]:
        """Check API health and connection status"""
        try:
            start = time.time()
            result = await self._make_request("GET", "/health")
            latency = (time.time() - start) * 1000
            
            return {
                "status": "healthy",
                "latency_ms": round(latency, 2),
                "circuit_breaker": self.circuit_breaker.state.value,
                "rate_limit_tokens": self.rate_limiter.tokens,
                "authenticated": self._is_token_valid(),
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "error": str(e),
                "circuit_breaker": self.circuit_breaker.state.value,
            }
    
    async def get_metrics(self) -> Dict[str, Any]:
        """Get client metrics"""
        return {
            "circuit_breaker_state": self.circuit_breaker.state.value,
            "circuit_breaker_failures": self.circuit_breaker.failure_count,
            "rate_limit_tokens": self.rate_limiter.tokens,
            "rate_limit_capacity": self.rate_limiter.config.burst_size,
            "token_valid": self._is_token_valid(),
            "token_expires_at": self.token_expires_at.isoformat() if self.token_expires_at else None,
        }


# Global client instance
soundtrack_client = SoundtrackClient()