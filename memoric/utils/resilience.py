"""
Resilience Utilities - Make external service calls robust.

When calling external services (vector DBs, LLMs, caches), things can fail.
This module provides utilities to handle failures gracefully:

- Retry with exponential backoff
- Circuit breakers to prevent cascading failures
- Timeouts to prevent hanging
- Fallback strategies

Use these for any external service call to harden your system.
"""

from __future__ import annotations

import functools
import time
from enum import Enum
from typing import Any, Callable, Optional, TypeVar

from .logger import get_logger

logger = get_logger(__name__)

T = TypeVar('T')


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"      # Normal operation
    OPEN = "open"          # Failures detected, reject requests
    HALF_OPEN = "half_open"  # Testing if service recovered


def retry_with_backoff(
    *,
    max_attempts: int = 3,
    initial_delay: float = 1.0,
    max_delay: float = 60.0,
    exponential_base: float = 2.0,
    exceptions: tuple = (Exception,),
    on_retry: Optional[Callable[[Exception, int], None]] = None,
):
    """
    Decorator to retry function with exponential backoff.

    Args:
        max_attempts: Maximum number of attempts
        initial_delay: Initial delay in seconds
        max_delay: Maximum delay in seconds
        exponential_base: Base for exponential backoff
        exceptions: Tuple of exceptions to catch and retry
        on_retry: Callback function(exception, attempt_number)

    Example:
        @retry_with_backoff(max_attempts=5, initial_delay=2.0)
        def call_external_api():
            response = requests.get("https://api.example.com")
            return response.json()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            delay = initial_delay

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)

                except exceptions as e:
                    if attempt == max_attempts:
                        logger.error(
                            f"Failed after {max_attempts} attempts: {func.__name__}",
                            extra={"error": str(e)}
                        )
                        raise

                    # Call retry callback if provided
                    if on_retry:
                        on_retry(e, attempt)

                    logger.warning(
                        f"Attempt {attempt}/{max_attempts} failed: {func.__name__}. "
                        f"Retrying in {delay:.1f}s...",
                        extra={"error": str(e)}
                    )

                    time.sleep(delay)

                    # Exponential backoff
                    delay = min(delay * exponential_base, max_delay)

            # Should never reach here, but for type safety
            raise RuntimeError(f"Retry logic failed for {func.__name__}")

        return wrapper
    return decorator


class CircuitBreaker:
    """
    Circuit breaker pattern to prevent cascading failures.

    States:
    - CLOSED: Normal operation, requests go through
    - OPEN: Too many failures, reject requests immediately
    - HALF_OPEN: Testing if service recovered

    Example:
        breaker = CircuitBreaker(
            failure_threshold=5,
            recovery_timeout=60.0
        )

        @breaker
        def call_unreliable_service():
            # Your external service call
            pass
    """

    def __init__(
        self,
        *,
        failure_threshold: int = 5,
        recovery_timeout: float = 60.0,
        expected_exception: type = Exception,
    ):
        """
        Initialize circuit breaker.

        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before trying again (half-open)
            expected_exception: Exception type that counts as failure
        """
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception

        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = CircuitState.CLOSED

        logger.info(
            f"Circuit breaker initialized (threshold: {failure_threshold}, "
            f"timeout: {recovery_timeout}s)"
        )

    def __call__(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to wrap function with circuit breaker."""
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Check circuit state
            if self.state == CircuitState.OPEN:
                # Check if recovery timeout passed
                if self.last_failure_time and \
                   time.time() - self.last_failure_time >= self.recovery_timeout:
                    logger.info(f"Circuit breaker half-open: {func.__name__}")
                    self.state = CircuitState.HALF_OPEN
                else:
                    raise RuntimeError(
                        f"Circuit breaker open for {func.__name__}. "
                        f"Service unavailable due to repeated failures."
                    )

            try:
                result = func(*args, **kwargs)

                # Success - reset if in half-open state
                if self.state == CircuitState.HALF_OPEN:
                    logger.info(f"Circuit breaker closed: {func.__name__}")
                    self.state = CircuitState.CLOSED
                    self.failure_count = 0

                return result

            except self.expected_exception as e:
                self.failure_count += 1
                self.last_failure_time = time.time()

                logger.warning(
                    f"Circuit breaker failure {self.failure_count}/{self.failure_threshold}: {func.__name__}",
                    extra={"error": str(e)}
                )

                # Open circuit if threshold reached
                if self.failure_count >= self.failure_threshold:
                    logger.error(f"Circuit breaker opened: {func.__name__}")
                    self.state = CircuitState.OPEN

                raise

        return wrapper

    def reset(self) -> None:
        """Manually reset circuit breaker."""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.last_failure_time = None
        logger.info("Circuit breaker manually reset")


def with_timeout(seconds: float):
    """
    Decorator to add timeout to function.

    Args:
        seconds: Timeout in seconds

    Example:
        @with_timeout(5.0)
        def slow_operation():
            # Operation that might hang
            pass

    Note: Uses signal on Unix, threading on Windows
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            import sys

            # Use signal on Unix systems
            if sys.platform != 'win32':
                import signal

                def timeout_handler(signum, frame):
                    raise TimeoutError(f"Function {func.__name__} timed out after {seconds}s")

                old_handler = signal.signal(signal.SIGALRM, timeout_handler)
                signal.alarm(int(seconds))

                try:
                    return func(*args, **kwargs)
                finally:
                    signal.alarm(0)
                    signal.signal(signal.SIGALRM, old_handler)

            # Use threading on Windows
            else:
                import threading

                result = [None]
                exception = [None]

                def target():
                    try:
                        result[0] = func(*args, **kwargs)
                    except Exception as e:
                        exception[0] = e

                thread = threading.Thread(target=target)
                thread.daemon = True
                thread.start()
                thread.join(seconds)

                if thread.is_alive():
                    raise TimeoutError(f"Function {func.__name__} timed out after {seconds}s")

                if exception[0]:
                    raise exception[0]

                return result[0]

        return wrapper
    return decorator


def fallback(fallback_func: Callable[..., T]):
    """
    Decorator to provide fallback function on failure.

    Args:
        fallback_func: Function to call if main function fails

    Example:
        def use_cache():
            return cached_data

        @fallback(use_cache)
        def fetch_from_api():
            return api.get_data()
    """
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> T:
            try:
                return func(*args, **kwargs)
            except Exception as e:
                logger.warning(
                    f"Function {func.__name__} failed, using fallback",
                    extra={"error": str(e)}
                )
                return fallback_func(*args, **kwargs)

        return wrapper
    return decorator


# Example usage combining multiple patterns
def create_resilient_caller(
    *,
    max_retries: int = 3,
    circuit_failure_threshold: int = 5,
    timeout_seconds: float = 30.0,
):
    """
    Create a resilient caller with retry, circuit breaker, and timeout.

    Example:
        resilient_call = create_resilient_caller(
            max_retries=3,
            circuit_failure_threshold=5,
            timeout_seconds=10.0
        )

        @resilient_call
        def call_external_service():
            return requests.get("https://api.example.com").json()
    """
    breaker = CircuitBreaker(failure_threshold=circuit_failure_threshold)

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        # Apply decorators in order: timeout -> retry -> circuit breaker
        decorated = func
        decorated = with_timeout(timeout_seconds)(decorated)
        decorated = retry_with_backoff(max_attempts=max_retries)(decorated)
        decorated = breaker(decorated)
        return decorated

    return decorator


__all__ = [
    "retry_with_backoff",
    "CircuitBreaker",
    "CircuitState",
    "with_timeout",
    "fallback",
    "create_resilient_caller",
]
