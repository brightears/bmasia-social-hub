"""Rate Limiter for API requests with sliding window and token bucket algorithms"""

import asyncio
import time
from typing import Dict, Optional, Tuple
from datetime import datetime, timedelta
from collections import deque
import logging

logger = logging.getLogger(__name__)


class RateLimiter:
    """
    Advanced rate limiter supporting both sliding window and token bucket algorithms.
    Optimized for high-throughput API operations with 1000 requests/minute limit.
    """
    
    def __init__(
        self,
        requests_per_minute: int = 1000,
        requests_per_second: int = 20,
        burst_size: int = 50,
        enable_adaptive: bool = True
    ):
        """
        Initialize rate limiter with configurable limits.
        
        Args:
            requests_per_minute: Maximum requests per minute (default: 1000)
            requests_per_second: Maximum requests per second (default: 20)
            burst_size: Maximum burst size for token bucket (default: 50)
            enable_adaptive: Enable adaptive rate limiting based on response times
        """
        # Rate limits
        self.requests_per_minute = requests_per_minute
        self.requests_per_second = requests_per_second
        self.burst_size = burst_size
        self.enable_adaptive = enable_adaptive
        
        # Sliding window for per-minute tracking
        self.minute_window: deque = deque()
        self.minute_lock = asyncio.Lock()
        
        # Token bucket for per-second rate limiting
        self.tokens = burst_size
        self.max_tokens = burst_size
        self.refill_rate = requests_per_second
        self.last_refill = time.time()
        self.token_lock = asyncio.Lock()
        
        # Adaptive rate limiting
        self.response_times: deque = deque(maxlen=100)
        self.error_count = 0
        self.success_count = 0
        self.adaptive_multiplier = 1.0
        
        # Metrics
        self.total_requests = 0
        self.blocked_requests = 0
        self.total_wait_time = 0.0
    
    async def acquire(self, priority: int = 5) -> float:
        """
        Acquire permission to make a request.
        
        Args:
            priority: Request priority (1-10, higher = more important)
        
        Returns:
            Wait time in seconds (0 if immediate)
        """
        wait_time = 0.0
        start_time = time.time()
        
        # Check minute-level rate limit
        async with self.minute_lock:
            wait_time = max(wait_time, await self._check_minute_limit())
        
        # Check second-level rate limit (token bucket)
        async with self.token_lock:
            token_wait = await self._check_token_bucket(priority)
            wait_time = max(wait_time, token_wait)
        
        # Apply wait time if needed
        if wait_time > 0:
            # Reduce wait time for high-priority requests
            adjusted_wait = wait_time * (1.0 - (priority - 5) * 0.1)
            adjusted_wait = max(0, min(adjusted_wait, wait_time))
            
            logger.debug(f"Rate limit: waiting {adjusted_wait:.2f}s (priority: {priority})")
            await asyncio.sleep(adjusted_wait)
            self.blocked_requests += 1
            self.total_wait_time += adjusted_wait
        
        # Update metrics
        self.total_requests += 1
        
        return time.time() - start_time
    
    async def _check_minute_limit(self) -> float:
        """Check minute-level rate limit using sliding window"""
        now = time.time()
        minute_ago = now - 60
        
        # Remove old entries
        while self.minute_window and self.minute_window[0] < minute_ago:
            self.minute_window.popleft()
        
        # Calculate effective limit with adaptive multiplier
        effective_limit = int(self.requests_per_minute * self.adaptive_multiplier)
        
        # Check if limit exceeded
        if len(self.minute_window) >= effective_limit:
            # Calculate wait time until oldest request expires
            oldest = self.minute_window[0]
            wait_time = (oldest + 60) - now
            return max(0, wait_time)
        
        # Add current request
        self.minute_window.append(now)
        return 0.0
    
    async def _check_token_bucket(self, priority: int) -> float:
        """Check second-level rate limit using token bucket algorithm"""
        now = time.time()
        
        # Refill tokens based on elapsed time
        elapsed = now - self.last_refill
        tokens_to_add = elapsed * self.refill_rate * self.adaptive_multiplier
        self.tokens = min(self.max_tokens, self.tokens + tokens_to_add)
        self.last_refill = now
        
        # Priority-based token cost (high priority = lower cost)
        token_cost = 1.0 - (priority - 5) * 0.05
        token_cost = max(0.5, min(1.5, token_cost))
        
        # Check if tokens available
        if self.tokens >= token_cost:
            self.tokens -= token_cost
            return 0.0
        
        # Calculate wait time for token availability
        tokens_needed = token_cost - self.tokens
        wait_time = tokens_needed / (self.refill_rate * self.adaptive_multiplier)
        return wait_time
    
    def report_response(self, response_time: float, success: bool):
        """
        Report response metrics for adaptive rate limiting.
        
        Args:
            response_time: Response time in seconds
            success: Whether request was successful
        """
        if not self.enable_adaptive:
            return
        
        self.response_times.append(response_time)
        
        if success:
            self.success_count += 1
            self.error_count = max(0, self.error_count - 1)  # Decay error count
        else:
            self.error_count += 1
        
        # Adjust adaptive multiplier based on performance
        self._update_adaptive_multiplier()
    
    def _update_adaptive_multiplier(self):
        """Update adaptive multiplier based on recent performance"""
        if len(self.response_times) < 10:
            return
        
        avg_response_time = sum(self.response_times) / len(self.response_times)
        error_rate = self.error_count / max(1, self.error_count + self.success_count)
        
        # Slow down if response times are high or errors are frequent
        if avg_response_time > 2.0 or error_rate > 0.1:
            self.adaptive_multiplier = max(0.5, self.adaptive_multiplier - 0.1)
            logger.info(f"Reducing rate limit multiplier to {self.adaptive_multiplier:.2f}")
        
        # Speed up if performance is good
        elif avg_response_time < 0.5 and error_rate < 0.01:
            self.adaptive_multiplier = min(1.2, self.adaptive_multiplier + 0.05)
            logger.info(f"Increasing rate limit multiplier to {self.adaptive_multiplier:.2f}")
    
    def get_current_usage(self) -> Dict[str, any]:
        """Get current rate limit usage statistics"""
        now = time.time()
        minute_ago = now - 60
        
        # Count requests in last minute
        recent_requests = sum(1 for t in self.minute_window if t > minute_ago)
        
        return {
            "requests_per_minute_limit": self.requests_per_minute,
            "requests_in_last_minute": recent_requests,
            "usage_percentage": (recent_requests / self.requests_per_minute) * 100,
            "available_tokens": self.tokens,
            "max_tokens": self.max_tokens,
            "adaptive_multiplier": self.adaptive_multiplier,
            "total_requests": self.total_requests,
            "blocked_requests": self.blocked_requests,
            "average_wait_time": self.total_wait_time / max(1, self.blocked_requests),
            "error_count": self.error_count,
            "success_count": self.success_count
        }
    
    def reset(self):
        """Reset rate limiter state"""
        self.minute_window.clear()
        self.tokens = self.max_tokens
        self.last_refill = time.time()
        self.response_times.clear()
        self.error_count = 0
        self.success_count = 0
        self.adaptive_multiplier = 1.0
        self.total_requests = 0
        self.blocked_requests = 0
        self.total_wait_time = 0.0
        logger.info("Rate limiter reset")
    
    async def wait_if_needed(self, estimated_requests: int) -> float:
        """
        Pre-emptively wait if bulk operation would exceed limits.
        
        Args:
            estimated_requests: Number of requests to be made
        
        Returns:
            Wait time in seconds
        """
        async with self.minute_lock:
            now = time.time()
            minute_ago = now - 60
            
            # Clean old entries
            while self.minute_window and self.minute_window[0] < minute_ago:
                self.minute_window.popleft()
            
            current_count = len(self.minute_window)
            effective_limit = int(self.requests_per_minute * self.adaptive_multiplier)
            
            if current_count + estimated_requests > effective_limit:
                # Calculate required wait time
                excess = (current_count + estimated_requests) - effective_limit
                wait_time = excess / (self.requests_per_minute / 60)  # Convert to seconds
                
                logger.info(
                    f"Pre-emptive rate limit wait: {wait_time:.2f}s for {estimated_requests} requests"
                )
                await asyncio.sleep(wait_time)
                return wait_time
        
        return 0.0


class DistributedRateLimiter(RateLimiter):
    """
    Distributed rate limiter using Redis for multi-instance coordination.
    Ensures rate limits are respected across all application instances.
    """
    
    def __init__(
        self,
        redis_client,
        key_prefix: str = "rate_limit:soundtrack",
        **kwargs
    ):
        super().__init__(**kwargs)
        self.redis = redis_client
        self.key_prefix = key_prefix
        
    async def acquire(self, priority: int = 5) -> float:
        """Acquire permission using distributed rate limiting"""
        wait_time = 0.0
        
        # Use Redis for distributed counting
        key = f"{self.key_prefix}:minute:{int(time.time() / 60)}"
        pipe = self.redis.pipeline()
        pipe.incr(key)
        pipe.expire(key, 70)  # Expire after 70 seconds
        results = await pipe.execute()
        
        current_count = results[0]
        effective_limit = int(self.requests_per_minute * self.adaptive_multiplier)
        
        if current_count > effective_limit:
            # Calculate distributed wait time
            wait_time = (current_count - effective_limit) / (self.requests_per_minute / 60)
            wait_time = wait_time * (1.0 - (priority - 5) * 0.1)  # Priority adjustment
            
            logger.debug(f"Distributed rate limit: waiting {wait_time:.2f}s")
            await asyncio.sleep(max(0, wait_time))
            self.blocked_requests += 1
            self.total_wait_time += wait_time
        
        self.total_requests += 1
        return wait_time