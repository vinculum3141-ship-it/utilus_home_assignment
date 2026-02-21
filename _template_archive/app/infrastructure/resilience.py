"""Resilience patterns - retry and circuit breaker for production."""

import time
from functools import wraps
from typing import Any, Callable, Type

from app.domain.exceptions import StorageUnavailableError
from app.infrastructure.logging import get_logger

logger = get_logger(__name__)


class CircuitBreaker:
    """Circuit breaker pattern for production resilience.
    
    States:
    - CLOSED: Normal operation, requests pass through
    - OPEN: Too many failures, requests fail immediately
    - HALF_OPEN: Testing if service recovered
    
    Production pattern from Netflix/AWS best practices.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exceptions: tuple = (StorageUnavailableError, ConnectionError, TimeoutError),
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            expected_exceptions: Exceptions that count as failures
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exceptions = expected_exceptions
        
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"
    
    def call(self, func: Callable, *args, **kwargs) -> Any:
        """Execute function with circuit breaker protection."""
        if self.state == "OPEN":
            if self._should_attempt_reset():
                self.state = "HALF_OPEN"
                logger.info("circuit_breaker_half_open", function=func.__name__)
            else:
                logger.warning(
                    "circuit_breaker_open",
                    function=func.__name__,
                    failure_count=self.failure_count,
                )
                raise StorageUnavailableError(
                    f"Circuit breaker OPEN for {func.__name__}. "
                    f"Service unavailable after {self.failure_count} failures."
                )
        
        try:
            result = func(*args, **kwargs)
            self._on_success()
            return result
        except self.expected_exceptions as e:
            self._on_failure()
            raise
    
    def _should_attempt_reset(self) -> bool:
        """Check if enough time has passed to attempt recovery."""
        if self.last_failure_time is None:
            return False
        return (time.time() - self.last_failure_time) >= self.recovery_timeout
    
    def _on_success(self):
        """Handle successful call."""
        if self.state == "HALF_OPEN":
            logger.info("circuit_breaker_closed", message="Service recovered")
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self):
        """Handle failed call."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(
                "circuit_breaker_opened",
                failure_count=self.failure_count,
                threshold=self.failure_threshold,
            )


# Global circuit breakers for each service
_circuit_breakers = {}


def get_circuit_breaker(name: str, **kwargs) -> CircuitBreaker:
    """Get or create circuit breaker for a service."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(**kwargs)
    return _circuit_breakers[name]


def with_retry(
    max_attempts: int = 3,
    backoff_factor: float = 2.0,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    retry_on: tuple = (StorageUnavailableError, ConnectionError, TimeoutError),
):
    """Retry decorator with exponential backoff.
    
    Production retry pattern with:
    - Exponential backoff
    - Maximum delay cap
    - Configurable retry exceptions
    
    Args:
        max_attempts: Maximum retry attempts
        backoff_factor: Multiplier for delay (2.0 = double each time)
        initial_delay: Starting delay in seconds
        max_delay: Maximum delay between retries
        retry_on: Tuple of exceptions to retry on
    
    Example:
        @with_retry(max_attempts=3, backoff_factor=2.0)
        def write_data(data):
            # May fail, will retry up to 3 times
            pass
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            delay = initial_delay
            last_exception = None
            
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except retry_on as e:
                    last_exception = e
                    
                    if attempt == max_attempts:
                        logger.error(
                            "retry_exhausted",
                            function=func.__name__,
                            attempts=attempt,
                            error=str(e),
                        )
                        raise
                    
                    logger.warning(
                        "retry_attempt",
                        function=func.__name__,
                        attempt=attempt,
                        max_attempts=max_attempts,
                        delay=delay,
                        error=str(e),
                    )
                    
                    time.sleep(delay)
                    delay = min(delay * backoff_factor, max_delay)
                except Exception as e:
                    # Don't retry on unexpected exceptions
                    logger.error(
                        "unexpected_error",
                        function=func.__name__,
                        error_type=type(e).__name__,
                        error=str(e),
                    )
                    raise
            
            # Should never reach here, but for safety
            if last_exception:
                raise last_exception
        
        return wrapper
    return decorator


def with_circuit_breaker(
    name: str,
    failure_threshold: int = 5,
    recovery_timeout: int = 60,
):
    """Circuit breaker decorator.
    
    Args:
        name: Circuit breaker name (usually service name)
        failure_threshold: Failures before opening circuit
        recovery_timeout: Seconds before attempting recovery
    
    Example:
        @with_circuit_breaker(name="storage", failure_threshold=5)
        def write_to_storage(data):
            # Protected by circuit breaker
            pass
    """
    def decorator(func: Callable) -> Callable:
        breaker = get_circuit_breaker(
            name,
            failure_threshold=failure_threshold,
            recovery_timeout=recovery_timeout,
        )
        
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return breaker.call(func, *args, **kwargs)
        
        return wrapper
    return decorator


def with_resilience(
    circuit_breaker_name: str,
    max_retry_attempts: int = 3,
    failure_threshold: int = 5,
):
    """Combined resilience: retry + circuit breaker.
    
    Production pattern combining both resilience mechanisms:
    1. Retry with exponential backoff for transient failures
    2. Circuit breaker to prevent cascade failures
    
    Args:
        circuit_breaker_name: Name for circuit breaker
        max_retry_attempts: Retry attempts per call
        failure_threshold: Failures before opening circuit
    
    Example:
        @with_resilience(circuit_breaker_name="storage", max_retry_attempts=3)
        def write_to_storage(data):
            # Protected by both retry and circuit breaker
            pass
    """
    def decorator(func: Callable) -> Callable:
        # Apply circuit breaker first, then retry
        @with_circuit_breaker(name=circuit_breaker_name, failure_threshold=failure_threshold)
        @with_retry(max_attempts=max_retry_attempts)
        @wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            return func(*args, **kwargs)
        return wrapper
    return decorator
