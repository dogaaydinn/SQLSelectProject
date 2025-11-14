"""
Caching Utilities
Redis-based caching with TTL and invalidation support
"""

import json
from typing import Any, Optional, Callable
from functools import wraps
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import logger


class CacheManager:
    """Redis cache manager."""

    def __init__(self):
        self.redis: Optional[aioredis.Redis] = None
        self.enabled = settings.CACHE_ENABLED

    async def connect(self) -> None:
        """Connect to Redis."""
        if not self.enabled:
            logger.info("Caching is disabled")
            return

        try:
            self.redis = await aioredis.from_url(
                settings.REDIS_URL,
                encoding="utf-8",
                decode_responses=True,
                max_connections=20,
            )
            await self.redis.ping()
            logger.info("Redis cache connected successfully")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.enabled = False

    async def disconnect(self) -> None:
        """Disconnect from Redis."""
        if self.redis:
            await self.redis.close()
            logger.info("Redis cache disconnected")

    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        if not self.enabled or not self.redis:
            return None

        try:
            value = await self.redis.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"Cache get error for key '{key}': {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl: Optional[int] = None,
    ) -> bool:
        """Set value in cache with TTL."""
        if not self.enabled or not self.redis:
            return False

        try:
            ttl = ttl or settings.REDIS_TTL
            serialized = json.dumps(value, default=str)
            await self.redis.setex(key, ttl, serialized)
            return True
        except Exception as e:
            logger.error(f"Cache set error for key '{key}': {e}")
            return False

    async def delete(self, key: str) -> bool:
        """Delete key from cache."""
        if not self.enabled or not self.redis:
            return False

        try:
            await self.redis.delete(key)
            return True
        except Exception as e:
            logger.error(f"Cache delete error for key '{key}': {e}")
            return False

    async def delete_pattern(self, pattern: str) -> int:
        """Delete all keys matching pattern."""
        if not self.enabled or not self.redis:
            return 0

        try:
            keys = await self.redis.keys(pattern)
            if keys:
                return await self.redis.delete(*keys)
            return 0
        except Exception as e:
            logger.error(f"Cache delete pattern error for '{pattern}': {e}")
            return 0

    async def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        if not self.enabled or not self.redis:
            return False

        try:
            return bool(await self.redis.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error for key '{key}': {e}")
            return False

    async def increment(self, key: str, amount: int = 1) -> int:
        """Increment counter."""
        if not self.enabled or not self.redis:
            return 0

        try:
            return await self.redis.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key '{key}': {e}")
            return 0

    async def get_ttl(self, key: str) -> int:
        """Get TTL for key."""
        if not self.enabled or not self.redis:
            return -1

        try:
            return await self.redis.ttl(key)
        except Exception as e:
            logger.error(f"Cache TTL error for key '{key}': {e}")
            return -1


# Global cache instance
cache_manager = CacheManager()


async def init_cache() -> None:
    """Initialize cache connection."""
    await cache_manager.connect()


async def close_cache() -> None:
    """Close cache connection."""
    await cache_manager.disconnect()


def cached(
    key_prefix: str,
    ttl: Optional[int] = None,
    key_builder: Optional[Callable] = None,
):
    """
    Decorator for caching function results.

    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds
        key_builder: Custom function to build cache key

    Example:
        @cached(key_prefix="employee", ttl=300)
        async def get_employee(emp_id: int):
            return await db.get_employee(emp_id)
    """

    def decorator(func: Callable):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = key_builder(*args, **kwargs)
            else:
                params = "_".join(str(arg) for arg in args)
                params += "_".join(f"{k}={v}" for k, v in kwargs.items())
                cache_key = f"{key_prefix}:{params}"

            # Try to get from cache
            cached_value = await cache_manager.get(cache_key)
            if cached_value is not None:
                logger.debug(f"Cache hit for key: {cache_key}")
                return cached_value

            # Execute function
            result = await func(*args, **kwargs)

            # Store in cache
            if result is not None:
                await cache_manager.set(cache_key, result, ttl)
                logger.debug(f"Cache set for key: {cache_key}")

            return result

        return wrapper

    return decorator
