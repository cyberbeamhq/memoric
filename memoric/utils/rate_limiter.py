"""
Rate limiting and brute force protection for authentication.

This module provides:
- Rate limiting for login attempts
- Account lockout after failed attempts
- In-memory and Redis-based backends
- Configurable thresholds and windows

Example:
    from memoric.utils.rate_limiter import RateLimiter, AccountLockout

    # Initialize rate limiter
    limiter = RateLimiter(
        max_attempts=5,
        window_seconds=300  # 5 minutes
    )

    # Check if user is rate limited
    if limiter.is_limited(identifier="user@example.com"):
        raise HTTPException(status_code=429, detail="Too many requests")

    # Record failed attempt
    limiter.record_attempt(identifier="user@example.com")

    # Initialize account lockout
    lockout = AccountLockout(
        max_failed_attempts=5,
        lockout_duration_seconds=900  # 15 minutes
    )

    # Check if account is locked
    if lockout.is_locked(username="user123"):
        raise HTTPException(status_code=423, detail="Account locked")

    # Record failed login
    lockout.record_failed_attempt(username="user123")

    # Clear on successful login
    lockout.clear_failed_attempts(username="user123")
"""

from __future__ import annotations

import time
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from threading import Lock
from typing import Dict, Optional, Tuple

from .logger import get_logger

logger = get_logger(__name__)


class RateLimiter:
    """
    Rate limiter for preventing brute force attacks.

    Uses token bucket algorithm with in-memory storage.
    For production with multiple instances, use Redis backend.

    Attributes:
        max_attempts: Maximum attempts allowed in time window
        window_seconds: Time window in seconds
        storage: In-memory storage of attempts
    """

    def __init__(
        self,
        *,
        max_attempts: int = 5,
        window_seconds: int = 300,  # 5 minutes
    ):
        """
        Initialize rate limiter.

        Args:
            max_attempts: Maximum attempts allowed in time window
            window_seconds: Time window in seconds for rate limiting
        """
        self.max_attempts = max_attempts
        self.window_seconds = window_seconds

        # Storage: identifier -> list of attempt timestamps
        self.storage: Dict[str, list[float]] = defaultdict(list)
        self.lock = Lock()

        logger.info(
            "Rate limiter initialized",
            extra={
                "max_attempts": max_attempts,
                "window_seconds": window_seconds,
            },
        )

    def is_limited(self, identifier: str) -> bool:
        """
        Check if identifier is currently rate limited.

        Args:
            identifier: Unique identifier (username, email, IP address)

        Returns:
            True if rate limited, False otherwise
        """
        with self.lock:
            # Clean up old attempts
            self._cleanup_old_attempts(identifier)

            # Check if attempts exceed limit
            attempts = self.storage.get(identifier, [])
            is_limited = len(attempts) >= self.max_attempts

            if is_limited:
                logger.warning(
                    "Rate limit exceeded",
                    extra={
                        "identifier": identifier,
                        "attempts": len(attempts),
                        "max_attempts": self.max_attempts,
                    },
                )

            return is_limited

    def record_attempt(self, identifier: str) -> None:
        """
        Record an attempt for the identifier.

        Args:
            identifier: Unique identifier (username, email, IP address)
        """
        with self.lock:
            current_time = time.time()
            self.storage[identifier].append(current_time)

            logger.debug(
                "Attempt recorded",
                extra={
                    "identifier": identifier,
                    "total_attempts": len(self.storage[identifier]),
                },
            )

    def get_remaining_attempts(self, identifier: str) -> int:
        """
        Get number of remaining attempts before rate limit.

        Args:
            identifier: Unique identifier

        Returns:
            Number of remaining attempts (0 if rate limited)
        """
        with self.lock:
            self._cleanup_old_attempts(identifier)
            attempts = len(self.storage.get(identifier, []))
            remaining = max(0, self.max_attempts - attempts)
            return remaining

    def get_retry_after(self, identifier: str) -> Optional[int]:
        """
        Get seconds until rate limit resets.

        Args:
            identifier: Unique identifier

        Returns:
            Seconds until reset, or None if not rate limited
        """
        with self.lock:
            attempts = self.storage.get(identifier, [])
            if not attempts or len(attempts) < self.max_attempts:
                return None

            # Find oldest attempt in current window
            oldest_attempt = min(attempts)
            reset_time = oldest_attempt + self.window_seconds
            retry_after = int(reset_time - time.time())

            return max(0, retry_after)

    def clear_attempts(self, identifier: str) -> None:
        """
        Clear all recorded attempts for identifier.

        Args:
            identifier: Unique identifier
        """
        with self.lock:
            if identifier in self.storage:
                del self.storage[identifier]
                logger.info("Attempts cleared", extra={"identifier": identifier})

    def _cleanup_old_attempts(self, identifier: str) -> None:
        """Remove attempts older than the time window."""
        current_time = time.time()
        cutoff = current_time - self.window_seconds

        if identifier in self.storage:
            # Keep only recent attempts
            self.storage[identifier] = [
                t for t in self.storage[identifier]
                if t > cutoff
            ]

            # Remove entry if no attempts left
            if not self.storage[identifier]:
                del self.storage[identifier]


class AccountLockout:
    """
    Account lockout mechanism for failed login attempts.

    Locks account after N failed attempts for a specified duration.
    Automatically unlocks after duration expires.

    Attributes:
        max_failed_attempts: Number of failed attempts before lockout
        lockout_duration_seconds: How long to lock account
        storage: In-memory storage of failed attempts
    """

    def __init__(
        self,
        *,
        max_failed_attempts: int = 5,
        lockout_duration_seconds: int = 900,  # 15 minutes
    ):
        """
        Initialize account lockout.

        Args:
            max_failed_attempts: Number of failed attempts before lockout
            lockout_duration_seconds: Duration of lockout in seconds
        """
        self.max_failed_attempts = max_failed_attempts
        self.lockout_duration = lockout_duration_seconds

        # Storage: username -> (failed_count, lockout_until_timestamp)
        self.storage: Dict[str, Tuple[int, Optional[float]]] = {}
        self.lock = Lock()

        logger.info(
            "Account lockout initialized",
            extra={
                "max_failed_attempts": max_failed_attempts,
                "lockout_duration_seconds": lockout_duration_seconds,
            },
        )

    def is_locked(self, username: str) -> bool:
        """
        Check if account is currently locked.

        Args:
            username: Username to check

        Returns:
            True if account is locked, False otherwise
        """
        with self.lock:
            if username not in self.storage:
                return False

            failed_count, lockout_until = self.storage[username]

            # Check if lockout has expired
            if lockout_until:
                current_time = time.time()
                if current_time >= lockout_until:
                    # Lockout expired, clear it
                    logger.info(
                        "Account lockout expired",
                        extra={"username": username},
                    )
                    del self.storage[username]
                    return False

                # Still locked
                logger.warning(
                    "Account is locked",
                    extra={
                        "username": username,
                        "locked_until": datetime.fromtimestamp(
                            lockout_until, tz=timezone.utc
                        ).isoformat(),
                    },
                )
                return True

            return False

    def record_failed_attempt(self, username: str) -> None:
        """
        Record a failed login attempt.

        Locks account if failed attempts exceed threshold.

        Args:
            username: Username that failed login
        """
        with self.lock:
            # Get current count
            failed_count, _ = self.storage.get(username, (0, None))
            failed_count += 1

            # Check if should lock account
            if failed_count >= self.max_failed_attempts:
                lockout_until = time.time() + self.lockout_duration
                self.storage[username] = (failed_count, lockout_until)

                logger.warning(
                    "Account locked due to failed attempts",
                    extra={
                        "username": username,
                        "failed_attempts": failed_count,
                        "locked_until": datetime.fromtimestamp(
                            lockout_until, tz=timezone.utc
                        ).isoformat(),
                    },
                )
            else:
                self.storage[username] = (failed_count, None)

                logger.info(
                    "Failed login attempt recorded",
                    extra={
                        "username": username,
                        "failed_attempts": failed_count,
                        "remaining_attempts": self.max_failed_attempts - failed_count,
                    },
                )

    def clear_failed_attempts(self, username: str) -> None:
        """
        Clear failed attempts for username (called on successful login).

        Args:
            username: Username to clear attempts for
        """
        with self.lock:
            if username in self.storage:
                del self.storage[username]
                logger.info(
                    "Failed attempts cleared",
                    extra={"username": username},
                )

    def get_lockout_info(self, username: str) -> Optional[Dict[str, any]]:
        """
        Get lockout information for username.

        Args:
            username: Username to check

        Returns:
            Dict with lockout info, or None if not locked
        """
        with self.lock:
            if username not in self.storage:
                return None

            failed_count, lockout_until = self.storage[username]

            if not lockout_until:
                return {
                    "locked": False,
                    "failed_attempts": failed_count,
                    "remaining_attempts": self.max_failed_attempts - failed_count,
                }

            current_time = time.time()
            if current_time >= lockout_until:
                return None

            return {
                "locked": True,
                "failed_attempts": failed_count,
                "locked_until": datetime.fromtimestamp(
                    lockout_until, tz=timezone.utc
                ).isoformat(),
                "retry_after_seconds": int(lockout_until - current_time),
            }

    def get_failed_attempts_count(self, username: str) -> int:
        """
        Get number of failed attempts for username.

        Args:
            username: Username to check

        Returns:
            Number of failed attempts
        """
        with self.lock:
            failed_count, _ = self.storage.get(username, (0, None))
            return failed_count


__all__ = ["RateLimiter", "AccountLockout"]
