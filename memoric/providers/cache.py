"""
Cache Providers - Plug-and-play caching for performance and rate limiting.

Use caching for:
- Rate limiting counters
- Session management
- Query result caching
- Frequently accessed data

Providers:
- Redis: Production-ready, distributed, persistent
- InMemory: Development/testing only
"""

from __future__ import annotations

import json
import os
import pickle
import time
from typing import Any, Dict, Optional

from .interfaces import CacheProvider
from ..utils.logger import get_logger

logger = get_logger(__name__)


class RedisCacheProvider(CacheProvider):
    """
    Redis cache provider.

    Production-ready caching with persistence and distribution.

    Setup:
        pip install redis
        # Run Redis locally:
        docker run -p 6379:6379 redis

    Example:
        cache = RedisCacheProvider(
            host="localhost",
            port=6379,
            prefix="memoric:"
        )
    """

    def __init__(
        self,
        *,
        host: str = "localhost",
        port: int = 6379,
        db: int = 0,
        password: Optional[str] = None,
        prefix: str = "memoric:",
        decode_responses: bool = True,
    ):
        """
        Initialize Redis cache.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Redis password (or REDIS_PASSWORD env var)
            prefix: Key prefix for namespacing
            decode_responses: Decode responses as strings
        """
        try:
            import redis
        except ImportError:
            raise ImportError(
                "Redis not installed. Run: pip install redis"
            )

        password = password or os.getenv("REDIS_PASSWORD")

        self.prefix = prefix
        self.client = redis.Redis(
            host=host,
            port=port,
            db=db,
            password=password,
            decode_responses=decode_responses,
            socket_connect_timeout=5,
            socket_timeout=5,
        )

        # Test connection
        try:
            self.client.ping()
            logger.info(f"Redis cache connected: {host}:{port}")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def _make_key(self, key: str) -> str:
        """Add prefix to key."""
        return f"{self.prefix}{key}"

    def get(self, key: str) -> Optional[Any]:
        """Get value from Redis."""
        try:
            value = self.client.get(self._make_key(key))
            if value is None:
                return None

            # Try to deserialize as JSON
            try:
                return json.loads(value)
            except (json.JSONDecodeError, TypeError):
                return value

        except Exception as e:
            logger.error(f"Failed to get from Redis: {e}")
            return None

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in Redis."""
        try:
            # Serialize value
            if isinstance(value, (dict, list)):
                serialized = json.dumps(value)
            elif isinstance(value, (str, int, float, bool)):
                serialized = str(value)
            else:
                serialized = pickle.dumps(value)

            return self.client.set(
                self._make_key(key),
                serialized,
                ex=ttl
            )
        except Exception as e:
            logger.error(f"Failed to set in Redis: {e}")
            return False

    def delete(self, key: str) -> bool:
        """Delete key from Redis."""
        try:
            return bool(self.client.delete(self._make_key(key)))
        except Exception as e:
            logger.error(f"Failed to delete from Redis: {e}")
            return False

    def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter in Redis."""
        try:
            return self.client.incrby(self._make_key(key), amount)
        except Exception as e:
            logger.error(f"Failed to increment in Redis: {e}")
            return 0

    def exists(self, key: str) -> bool:
        """Check if key exists in Redis."""
        try:
            return bool(self.client.exists(self._make_key(key)))
        except Exception as e:
            logger.error(f"Failed to check existence in Redis: {e}")
            return False

    def health_check(self) -> bool:
        """Check Redis health."""
        try:
            return self.client.ping()
        except Exception:
            return False

    def set_with_expiry(self, key: str, value: Any, seconds: int) -> bool:
        """Set value with expiry (alias for set with ttl)."""
        return self.set(key, value, ttl=seconds)

    def get_ttl(self, key: str) -> Optional[int]:
        """Get remaining TTL for key."""
        try:
            ttl = self.client.ttl(self._make_key(key))
            return ttl if ttl >= 0 else None
        except Exception as e:
            logger.error(f"Failed to get TTL from Redis: {e}")
            return None


class InMemoryCacheProvider(CacheProvider):
    """
    In-memory cache provider for development/testing.

    NOT for production:
    - Data lost on restart
    - No distribution across instances
    - Limited memory

    Useful for:
    - Local development
    - Testing
    - Single-instance deployments

    Example:
        cache = InMemoryCacheProvider()
    """

    def __init__(self):
        """Initialize in-memory cache."""
        self.data: Dict[str, Any] = {}
        self.expiry: Dict[str, float] = {}
        logger.info("In-memory cache initialized (development only)")

    def _is_expired(self, key: str) -> bool:
        """Check if key has expired."""
        if key not in self.expiry:
            return False

        if time.time() > self.expiry[key]:
            # Clean up expired key
            del self.data[key]
            del self.expiry[key]
            return True

        return False

    def get(self, key: str) -> Optional[Any]:
        """Get value from memory."""
        if key not in self.data or self._is_expired(key):
            return None
        return self.data[key]

    def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in memory."""
        self.data[key] = value

        if ttl is not None:
            self.expiry[key] = time.time() + ttl
        elif key in self.expiry:
            del self.expiry[key]

        return True

    def delete(self, key: str) -> bool:
        """Delete key from memory."""
        if key in self.data:
            del self.data[key]
            if key in self.expiry:
                del self.expiry[key]
            return True
        return False

    def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter in memory."""
        current = self.data.get(key, 0)
        if not isinstance(current, (int, float)):
            current = 0

        new_value = int(current) + amount
        self.data[key] = new_value
        return new_value

    def exists(self, key: str) -> bool:
        """Check if key exists in memory."""
        return key in self.data and not self._is_expired(key)

    def health_check(self) -> bool:
        """Always healthy for in-memory cache."""
        return True


__all__ = [
    "RedisCacheProvider",
    "InMemoryCacheProvider",
]
