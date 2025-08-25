"""Connection pool manager for efficient HTTP connection reuse"""

import asyncio
from typing import Optional, Dict, Any, List
import httpx
from datetime import datetime, timedelta
import logging
from contextlib import asynccontextmanager

logger = logging.getLogger(__name__)


class ConnectionPoolManager:
    """
    Manages connection pools for high-throughput API operations.
    Optimized for 10,000+ concurrent connections with health monitoring.
    """
    
    def __init__(
        self,
        max_connections: int = 100,
        max_keepalive_connections: int = 50,
        keepalive_expiry: int = 30,
        timeout: float = 30.0,
        retries: int = 3,
        verify_ssl: bool = True
    ):
        """
        Initialize connection pool manager.
        
        Args:
            max_connections: Maximum number of connections in pool
            max_keepalive_connections: Maximum idle connections to keep
            keepalive_expiry: Seconds before closing idle connections
            timeout: Default timeout for requests
            retries: Number of retries for failed requests
            verify_ssl: Whether to verify SSL certificates
        """
        self.max_connections = max_connections
        self.max_keepalive_connections = max_keepalive_connections
        self.keepalive_expiry = keepalive_expiry
        self.timeout = timeout
        self.retries = retries
        self.verify_ssl = verify_ssl
        
        # Connection pools by base URL
        self._pools: Dict[str, httpx.AsyncClient] = {}
        self._pool_locks: Dict[str, asyncio.Lock] = {}
        
        # Connection health tracking
        self._connection_stats: Dict[str, Dict] = {}
        self._last_cleanup = datetime.utcnow()
        
        # Performance metrics
        self.total_requests = 0
        self.active_connections = 0
        self.failed_connections = 0
        self.connection_reuse_count = 0
        
        # Cleanup task
        self._cleanup_task: Optional[asyncio.Task] = None
    
    async def start(self):
        """Start the connection pool manager and cleanup task"""
        self._cleanup_task = asyncio.create_task(self._periodic_cleanup())
        logger.info(f"Connection pool manager started with max {self.max_connections} connections")
    
    async def stop(self):
        """Stop the connection pool manager and close all connections"""
        if self._cleanup_task:
            self._cleanup_task.cancel()
            try:
                await self._cleanup_task
            except asyncio.CancelledError:
                pass
        
        # Close all connection pools
        for url, client in self._pools.items():
            await client.aclose()
            logger.info(f"Closed connection pool for {url}")
        
        self._pools.clear()
        self._pool_locks.clear()
        self._connection_stats.clear()
    
    async def get_client(self, base_url: str) -> httpx.AsyncClient:
        """
        Get or create HTTP client for given base URL.
        
        Args:
            base_url: Base URL for the API
        
        Returns:
            Configured HTTP client with connection pooling
        """
        if base_url not in self._pools:
            async with self._get_lock(base_url):
                # Double-check after acquiring lock
                if base_url not in self._pools:
                    await self._create_pool(base_url)
        
        self.connection_reuse_count += 1
        return self._pools[base_url]
    
    @asynccontextmanager
    async def get_connection(self, base_url: str):
        """
        Context manager for getting a connection from the pool.
        
        Usage:
            async with pool_manager.get_connection(url) as client:
                response = await client.get("/endpoint")
        """
        client = await self.get_client(base_url)
        self.active_connections += 1
        
        try:
            yield client
        finally:
            self.active_connections -= 1
            self._update_stats(base_url, success=True)
    
    async def _create_pool(self, base_url: str):
        """Create new connection pool for base URL"""
        limits = httpx.Limits(
            max_connections=self.max_connections,
            max_keepalive_connections=self.max_keepalive_connections,
            keepalive_expiry=self.keepalive_expiry
        )
        
        timeout_config = httpx.Timeout(
            connect=5.0,
            read=self.timeout,
            write=10.0,
            pool=30.0
        )
        
        # Configure transport with connection pooling
        transport = httpx.AsyncHTTPTransport(
            retries=self.retries,
            verify=self.verify_ssl,
            http2=True,  # Enable HTTP/2 for better performance
            limits=limits
        )
        
        client = httpx.AsyncClient(
            base_url=base_url,
            transport=transport,
            timeout=timeout_config,
            follow_redirects=True,
            headers={
                "User-Agent": "BMA-Social-Soundtrack-Client/1.0",
                "Accept": "application/json",
                "Accept-Encoding": "gzip, deflate",
                "Connection": "keep-alive"
            }
        )
        
        self._pools[base_url] = client
        self._connection_stats[base_url] = {
            "created_at": datetime.utcnow(),
            "requests": 0,
            "failures": 0,
            "last_used": datetime.utcnow(),
            "response_times": []
        }
        
        logger.info(f"Created connection pool for {base_url} with {self.max_connections} max connections")
    
    def _get_lock(self, base_url: str) -> asyncio.Lock:
        """Get or create lock for base URL"""
        if base_url not in self._pool_locks:
            self._pool_locks[base_url] = asyncio.Lock()
        return self._pool_locks[base_url]
    
    def _update_stats(self, base_url: str, success: bool, response_time: Optional[float] = None):
        """Update connection statistics"""
        if base_url in self._connection_stats:
            stats = self._connection_stats[base_url]
            stats["requests"] += 1
            stats["last_used"] = datetime.utcnow()
            
            if not success:
                stats["failures"] += 1
                self.failed_connections += 1
            
            if response_time is not None:
                # Keep last 100 response times
                stats["response_times"].append(response_time)
                if len(stats["response_times"]) > 100:
                    stats["response_times"] = stats["response_times"][-100:]
        
        self.total_requests += 1
    
    async def _periodic_cleanup(self):
        """Periodically clean up idle connections"""
        while True:
            try:
                await asyncio.sleep(60)  # Run every minute
                await self._cleanup_idle_pools()
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in periodic cleanup: {e}")
    
    async def _cleanup_idle_pools(self):
        """Clean up idle connection pools"""
        now = datetime.utcnow()
        idle_threshold = timedelta(minutes=10)
        
        pools_to_remove = []
        
        for base_url, stats in self._connection_stats.items():
            if now - stats["last_used"] > idle_threshold:
                pools_to_remove.append(base_url)
        
        for base_url in pools_to_remove:
            async with self._get_lock(base_url):
                if base_url in self._pools:
                    await self._pools[base_url].aclose()
                    del self._pools[base_url]
                    del self._connection_stats[base_url]
                    logger.info(f"Cleaned up idle connection pool for {base_url}")
    
    async def execute_request(
        self,
        method: str,
        url: str,
        base_url: Optional[str] = None,
        **kwargs
    ) -> httpx.Response:
        """
        Execute HTTP request with connection pooling and retry logic.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Request URL (full or relative)
            base_url: Base URL for the API (if url is relative)
            **kwargs: Additional request parameters
        
        Returns:
            HTTP response
        """
        # Determine base URL
        if base_url is None:
            # Extract base URL from full URL
            from urllib.parse import urlparse
            parsed = urlparse(url)
            base_url = f"{parsed.scheme}://{parsed.netloc}"
            url = parsed.path + (f"?{parsed.query}" if parsed.query else "")
        
        start_time = datetime.utcnow()
        last_exception = None
        
        for attempt in range(self.retries):
            try:
                async with self.get_connection(base_url) as client:
                    response = await client.request(method, url, **kwargs)
                    
                    # Update statistics
                    response_time = (datetime.utcnow() - start_time).total_seconds()
                    self._update_stats(base_url, success=True, response_time=response_time)
                    
                    return response
                    
            except Exception as e:
                last_exception = e
                self._update_stats(base_url, success=False)
                
                if attempt < self.retries - 1:
                    wait_time = 2 ** attempt  # Exponential backoff
                    logger.warning(
                        f"Request failed (attempt {attempt + 1}/{self.retries}): {e}. "
                        f"Retrying in {wait_time}s..."
                    )
                    await asyncio.sleep(wait_time)
                else:
                    logger.error(f"Request failed after {self.retries} attempts: {e}")
        
        raise last_exception
    
    def get_pool_stats(self) -> Dict[str, Any]:
        """Get connection pool statistics"""
        stats = {
            "total_pools": len(self._pools),
            "total_requests": self.total_requests,
            "active_connections": self.active_connections,
            "failed_connections": self.failed_connections,
            "connection_reuse_count": self.connection_reuse_count,
            "pools": {}
        }
        
        for base_url, pool_stats in self._connection_stats.items():
            avg_response_time = 0
            if pool_stats["response_times"]:
                avg_response_time = sum(pool_stats["response_times"]) / len(pool_stats["response_times"])
            
            stats["pools"][base_url] = {
                "requests": pool_stats["requests"],
                "failures": pool_stats["failures"],
                "failure_rate": pool_stats["failures"] / max(1, pool_stats["requests"]),
                "average_response_time": avg_response_time,
                "last_used": pool_stats["last_used"].isoformat(),
                "age_minutes": (datetime.utcnow() - pool_stats["created_at"]).total_seconds() / 60
            }
        
        return stats
    
    async def health_check(self, base_url: str, endpoint: str = "/health") -> bool:
        """
        Perform health check on connection pool.
        
        Args:
            base_url: Base URL to check
            endpoint: Health check endpoint
        
        Returns:
            True if healthy, False otherwise
        """
        try:
            response = await self.execute_request(
                "GET",
                endpoint,
                base_url=base_url,
                timeout=5.0
            )
            return response.status_code < 500
        except Exception as e:
            logger.error(f"Health check failed for {base_url}: {e}")
            return False


class LoadBalancedPool:
    """
    Load-balanced connection pool across multiple API endpoints.
    Useful for distributing load across multiple Soundtrack API servers.
    """
    
    def __init__(self, endpoints: List[str], **pool_kwargs):
        """
        Initialize load-balanced pool.
        
        Args:
            endpoints: List of API endpoint URLs
            **pool_kwargs: Arguments for ConnectionPoolManager
        """
        self.endpoints = endpoints
        self.pools = [ConnectionPoolManager(**pool_kwargs) for _ in endpoints]
        self.current_index = 0
        self._lock = asyncio.Lock()
        
        # Health tracking
        self.endpoint_health: Dict[str, bool] = {ep: True for ep in endpoints}
        self.endpoint_latency: Dict[str, float] = {ep: 0.0 for ep in endpoints}
    
    async def start(self):
        """Start all connection pools"""
        for pool in self.pools:
            await pool.start()
    
    async def stop(self):
        """Stop all connection pools"""
        for pool in self.pools:
            await pool.stop()
    
    async def get_pool(self) -> tuple[str, ConnectionPoolManager]:
        """
        Get next available connection pool using round-robin with health awareness.
        
        Returns:
            Tuple of (endpoint, pool)
        """
        async with self._lock:
            # Try to find healthy endpoint
            attempts = 0
            while attempts < len(self.endpoints):
                endpoint = self.endpoints[self.current_index]
                pool = self.pools[self.current_index]
                
                self.current_index = (self.current_index + 1) % len(self.endpoints)
                
                if self.endpoint_health.get(endpoint, True):
                    return endpoint, pool
                
                attempts += 1
            
            # All endpoints unhealthy, return first one
            return self.endpoints[0], self.pools[0]
    
    async def execute_request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Execute request on load-balanced pool"""
        endpoint, pool = await self.get_pool()
        
        try:
            start_time = datetime.utcnow()
            response = await pool.execute_request(method, path, base_url=endpoint, **kwargs)
            
            # Update latency
            latency = (datetime.utcnow() - start_time).total_seconds()
            self.endpoint_latency[endpoint] = latency
            
            # Mark as healthy
            self.endpoint_health[endpoint] = True
            
            return response
            
        except Exception as e:
            # Mark as unhealthy
            self.endpoint_health[endpoint] = False
            logger.warning(f"Endpoint {endpoint} marked as unhealthy: {e}")
            raise