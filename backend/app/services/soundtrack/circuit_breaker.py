"""Circuit Breaker pattern implementation for resilient API calls"""

import asyncio
import time
from typing import Optional, Callable, Any, Dict
from datetime import datetime, timedelta
from enum import Enum
import logging
from functools import wraps

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""
    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """
    Circuit breaker implementation to prevent cascade failures.
    Monitors API health and temporarily blocks requests when failures exceed threshold.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: type = Exception,
        success_threshold: int = 2,
        failure_rate_threshold: float = 0.5,
        monitoring_window: int = 60
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exception: Exception type to catch
            success_threshold: Successes needed to close circuit from half-open
            failure_rate_threshold: Failure rate to trigger open state (0.0-1.0)
            monitoring_window: Time window in seconds for rate calculation
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.success_threshold = success_threshold
        self.failure_rate_threshold = failure_rate_threshold
        self.monitoring_window = monitoring_window
        
        # State management
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._last_success_time: Optional[datetime] = None
        self._circuit_open_time: Optional[datetime] = None
        
        # Request tracking for rate calculation
        self._request_history: list = []  # List of (timestamp, success) tuples
        
        # Callbacks
        self._on_open_callbacks: list = []
        self._on_close_callbacks: list = []
        
        # Metrics
        self.total_requests = 0
        self.total_failures = 0
        self.total_successes = 0
        self.total_rejections = 0
        self.state_changes = 0
        
        # Lock for thread safety
        self._lock = asyncio.Lock()
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state"""
        return self._state
    
    @property
    def is_closed(self) -> bool:
        """Check if circuit is closed (normal operation)"""
        return self._state == CircuitState.CLOSED
    
    @property
    def is_open(self) -> bool:
        """Check if circuit is open (rejecting requests)"""
        return self._state == CircuitState.OPEN
    
    @property
    def is_half_open(self) -> bool:
        """Check if circuit is half-open (testing recovery)"""
        return self._state == CircuitState.HALF_OPEN
    
    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function through circuit breaker.
        
        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments
        
        Returns:
            Function result
        
        Raises:
            CircuitBreakerError: If circuit is open
            Exception: If function fails
        """
        async with self._lock:
            # Check if we should transition from OPEN to HALF_OPEN
            if self.is_open:
                if self._should_attempt_reset():
                    await self._transition_to_half_open()
                else:
                    self.total_rejections += 1
                    raise CircuitBreakerError(
                        f"Circuit breaker is OPEN. Requests blocked until "
                        f"{self._get_recovery_time()}"
                    )
            
            self.total_requests += 1
        
        # Execute the function
        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        
        except self.expected_exception as e:
            await self._on_failure(e)
            raise
    
    def decorator(self, func: Callable) -> Callable:
        """
        Decorator to wrap async functions with circuit breaker.
        
        Usage:
            @circuit_breaker.decorator
            async def api_call():
                ...
        """
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await self.call(func, *args, **kwargs)
        return wrapper
    
    async def _on_success(self):
        """Handle successful request"""
        async with self._lock:
            self.total_successes += 1
            self._last_success_time = datetime.utcnow()
            
            # Track request for rate calculation
            self._track_request(success=True)
            
            if self.is_half_open:
                self._success_count += 1
                if self._success_count >= self.success_threshold:
                    await self._transition_to_closed()
            
            elif self.is_closed:
                # Reset failure count on success in closed state
                self._failure_count = 0
    
    async def _on_failure(self, exception: Exception):
        """Handle failed request"""
        async with self._lock:
            self.total_failures += 1
            self._failure_count += 1
            self._last_failure_time = datetime.utcnow()
            
            # Track request for rate calculation
            self._track_request(success=False)
            
            logger.warning(
                f"Circuit breaker failure {self._failure_count}/{self.failure_threshold}: {exception}"
            )
            
            if self.is_half_open:
                # Any failure in half-open state reopens the circuit
                await self._transition_to_open()
            
            elif self.is_closed:
                # Check if we should open the circuit
                if self._should_open_circuit():
                    await self._transition_to_open()
    
    def _track_request(self, success: bool):
        """Track request for rate calculation"""
        now = time.time()
        self._request_history.append((now, success))
        
        # Remove old entries outside monitoring window
        cutoff = now - self.monitoring_window
        self._request_history = [
            (t, s) for t, s in self._request_history if t > cutoff
        ]
    
    def _should_open_circuit(self) -> bool:
        """Determine if circuit should open based on failure criteria"""
        # Check absolute failure threshold
        if self._failure_count >= self.failure_threshold:
            return True
        
        # Check failure rate
        if len(self._request_history) >= 10:  # Minimum samples
            recent_failures = sum(1 for _, success in self._request_history if not success)
            failure_rate = recent_failures / len(self._request_history)
            
            if failure_rate >= self.failure_rate_threshold:
                logger.info(f"Opening circuit due to failure rate: {failure_rate:.2%}")
                return True
        
        return False
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt reset"""
        if not self._circuit_open_time:
            return True
        
        elapsed = (datetime.utcnow() - self._circuit_open_time).total_seconds()
        return elapsed >= self.recovery_timeout
    
    def _get_recovery_time(self) -> datetime:
        """Get estimated recovery time"""
        if not self._circuit_open_time:
            return datetime.utcnow()
        
        return self._circuit_open_time + timedelta(seconds=self.recovery_timeout)
    
    async def _transition_to_open(self):
        """Transition to OPEN state"""
        self._state = CircuitState.OPEN
        self._circuit_open_time = datetime.utcnow()
        self._failure_count = 0
        self._success_count = 0
        self.state_changes += 1
        
        logger.error(
            f"Circuit breaker OPENED. Will attempt recovery at {self._get_recovery_time()}"
        )
        
        # Execute callbacks
        for callback in self._on_open_callbacks:
            try:
                await callback()
            except Exception as e:
                logger.error(f"Error in circuit open callback: {e}")
    
    async def _transition_to_half_open(self):
        """Transition to HALF_OPEN state"""
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        self._failure_count = 0
        self.state_changes += 1
        
        logger.info("Circuit breaker transitioned to HALF_OPEN. Testing recovery...")
    
    async def _transition_to_closed(self):
        """Transition to CLOSED state"""
        self._state = CircuitState.CLOSED
        self._circuit_open_time = None
        self._failure_count = 0
        self._success_count = 0
        self.state_changes += 1
        
        logger.info("Circuit breaker CLOSED. Normal operation resumed.")
        
        # Execute callbacks
        for callback in self._on_close_callbacks:
            try:
                await callback()
            except Exception as e:
                logger.error(f"Error in circuit close callback: {e}")
    
    def add_on_open_callback(self, callback: Callable):
        """Add callback to execute when circuit opens"""
        self._on_open_callbacks.append(callback)
    
    def add_on_close_callback(self, callback: Callable):
        """Add callback to execute when circuit closes"""
        self._on_close_callbacks.append(callback)
    
    async def reset(self):
        """Manually reset circuit breaker to closed state"""
        async with self._lock:
            self._state = CircuitState.CLOSED
            self._failure_count = 0
            self._success_count = 0
            self._circuit_open_time = None
            self._request_history.clear()
            
            logger.info("Circuit breaker manually reset to CLOSED state")
    
    async def trip(self):
        """Manually trip circuit breaker to open state"""
        async with self._lock:
            await self._transition_to_open()
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics"""
        # Calculate current failure rate
        failure_rate = 0.0
        if self._request_history:
            recent_failures = sum(1 for _, success in self._request_history if not success)
            failure_rate = recent_failures / len(self._request_history)
        
        return {
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "total_requests": self.total_requests,
            "total_failures": self.total_failures,
            "total_successes": self.total_successes,
            "total_rejections": self.total_rejections,
            "failure_rate": failure_rate,
            "state_changes": self.state_changes,
            "last_failure_time": self._last_failure_time.isoformat() if self._last_failure_time else None,
            "last_success_time": self._last_success_time.isoformat() if self._last_success_time else None,
            "recovery_time": self._get_recovery_time().isoformat() if self.is_open else None
        }


class CircuitBreakerError(Exception):
    """Exception raised when circuit breaker is open"""
    pass


class MultiCircuitBreaker:
    """
    Manages multiple circuit breakers for different endpoints or services.
    Useful for managing different failure thresholds per endpoint.
    """
    
    def __init__(self, default_config: Optional[Dict[str, Any]] = None):
        """
        Initialize multi-circuit breaker manager.
        
        Args:
            default_config: Default configuration for new circuit breakers
        """
        self.breakers: Dict[str, CircuitBreaker] = {}
        self.default_config = default_config or {
            "failure_threshold": 5,
            "recovery_timeout": 60,
            "success_threshold": 2
        }
    
    def get_breaker(self, name: str) -> CircuitBreaker:
        """Get or create circuit breaker for given name"""
        if name not in self.breakers:
            self.breakers[name] = CircuitBreaker(**self.default_config)
            logger.info(f"Created new circuit breaker: {name}")
        
        return self.breakers[name]
    
    async def call(self, name: str, func: Callable, *args, **kwargs) -> Any:
        """Execute function through named circuit breaker"""
        breaker = self.get_breaker(name)
        return await breaker.call(func, *args, **kwargs)
    
    async def reset_all(self):
        """Reset all circuit breakers"""
        for name, breaker in self.breakers.items():
            await breaker.reset()
            logger.info(f"Reset circuit breaker: {name}")
    
    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers"""
        return {
            name: breaker.get_metrics()
            for name, breaker in self.breakers.items()
        }