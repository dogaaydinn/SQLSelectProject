"""
Unit Tests for Cache Utility
Tests Redis caching functionality, decorators, and cache management
"""

import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from app.utils.cache import CacheManager, cached


@pytest.mark.unit
@pytest.mark.cache
class TestCacheManager:
    """Test CacheManager class."""

    @pytest.fixture
    def cache_manager(self):
        """Create a cache manager instance."""
        manager = CacheManager()
        manager.redis = AsyncMock()
        return manager

    async def test_connect(self, cache_manager):
        """Test cache connection."""
        with patch('app.utils.cache.Redis') as mock_redis:
            mock_redis.from_url.return_value = AsyncMock()
            await cache_manager.connect()
            assert cache_manager.redis is not None

    async def test_disconnect(self, cache_manager):
        """Test cache disconnection."""
        cache_manager.redis.aclose = AsyncMock()
        await cache_manager.disconnect()
        cache_manager.redis.aclose.assert_called_once()

    async def test_get_success(self, cache_manager):
        """Test successful cache retrieval."""
        cache_manager.redis.get.return_value = b'{"key": "value"}'

        result = await cache_manager.get("test_key")

        assert result == {"key": "value"}
        cache_manager.redis.get.assert_called_once_with("test_key")

    async def test_get_not_found(self, cache_manager):
        """Test cache retrieval when key doesn't exist."""
        cache_manager.redis.get.return_value = None

        result = await cache_manager.get("nonexistent_key")

        assert result is None

    async def test_get_invalid_json(self, cache_manager):
        """Test cache retrieval with invalid JSON."""
        cache_manager.redis.get.return_value = b'invalid json'

        result = await cache_manager.get("invalid_key")

        assert result is None

    async def test_set_success(self, cache_manager):
        """Test successful cache setting."""
        cache_manager.redis.setex = AsyncMock()
        data = {"key": "value"}

        await cache_manager.set("test_key", data, ttl=300)

        cache_manager.redis.setex.assert_called_once()
        args = cache_manager.redis.setex.call_args
        assert args[0][0] == "test_key"
        assert args[0][1] == 300

    async def test_set_with_default_ttl(self, cache_manager):
        """Test cache setting with default TTL."""
        cache_manager.redis.setex = AsyncMock()
        data = {"key": "value"}

        await cache_manager.set("test_key", data)

        cache_manager.redis.setex.assert_called_once()

    async def test_delete_success(self, cache_manager):
        """Test successful cache deletion."""
        cache_manager.redis.delete = AsyncMock(return_value=1)

        result = await cache_manager.delete("test_key")

        assert result is True
        cache_manager.redis.delete.assert_called_once_with("test_key")

    async def test_delete_not_found(self, cache_manager):
        """Test cache deletion when key doesn't exist."""
        cache_manager.redis.delete = AsyncMock(return_value=0)

        result = await cache_manager.delete("nonexistent_key")

        assert result is False

    async def test_delete_pattern(self, cache_manager):
        """Test deletion by pattern."""
        cache_manager.redis.scan = AsyncMock(return_value=(0, [b"key1", b"key2"]))
        cache_manager.redis.delete = AsyncMock()

        count = await cache_manager.delete_pattern("test:*")

        assert count == 2
        cache_manager.redis.delete.assert_called()

    async def test_clear_all(self, cache_manager):
        """Test clearing all cache."""
        cache_manager.redis.flushdb = AsyncMock()

        await cache_manager.clear()

        cache_manager.redis.flushdb.assert_called_once()

    async def test_exists(self, cache_manager):
        """Test checking if key exists."""
        cache_manager.redis.exists = AsyncMock(return_value=1)

        result = await cache_manager.exists("test_key")

        assert result is True
        cache_manager.redis.exists.assert_called_once_with("test_key")

    async def test_exists_not_found(self, cache_manager):
        """Test checking if key exists when it doesn't."""
        cache_manager.redis.exists = AsyncMock(return_value=0)

        result = await cache_manager.exists("nonexistent_key")

        assert result is False

    async def test_error_handling(self, cache_manager):
        """Test error handling in cache operations."""
        cache_manager.redis.get.side_effect = Exception("Redis error")

        result = await cache_manager.get("test_key")

        assert result is None


@pytest.mark.unit
@pytest.mark.cache
class TestCachedDecorator:
    """Test @cached decorator."""

    @pytest.fixture
    def mock_cache(self):
        """Create a mock cache manager."""
        with patch('app.utils.cache.cache_manager') as mock:
            mock.get = AsyncMock()
            mock.set = AsyncMock()
            yield mock

    async def test_cached_decorator_cache_hit(self, mock_cache):
        """Test cached decorator with cache hit."""
        mock_cache.get.return_value = {"result": "cached"}

        @cached(key_prefix="test", ttl=300)
        async def test_function(arg1, arg2):
            return {"result": "fresh"}

        result = await test_function("val1", "val2")

        assert result == {"result": "cached"}
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_not_called()

    async def test_cached_decorator_cache_miss(self, mock_cache):
        """Test cached decorator with cache miss."""
        mock_cache.get.return_value = None

        @cached(key_prefix="test", ttl=300)
        async def test_function(arg1, arg2):
            return {"result": "fresh"}

        result = await test_function("val1", "val2")

        assert result == {"result": "fresh"}
        mock_cache.get.assert_called_once()
        mock_cache.set.assert_called_once()

    async def test_cached_decorator_key_generation(self, mock_cache):
        """Test that cached decorator generates proper cache keys."""
        mock_cache.get.return_value = None

        @cached(key_prefix="test", ttl=300)
        async def test_function(arg1, arg2):
            return {"result": "data"}

        await test_function("val1", "val2")

        # Check that cache key was generated with arguments
        call_args = mock_cache.get.call_args
        cache_key = call_args[0][0]
        assert cache_key.startswith("test:")

    async def test_cached_decorator_with_ttl(self, mock_cache):
        """Test cached decorator respects TTL."""
        mock_cache.get.return_value = None

        @cached(key_prefix="test", ttl=600)
        async def test_function():
            return {"result": "data"}

        await test_function()

        # Verify TTL was passed to set
        call_args = mock_cache.set.call_args
        assert call_args[1]["ttl"] == 600

    async def test_cached_decorator_error_handling(self, mock_cache):
        """Test cached decorator handles cache errors gracefully."""
        mock_cache.get.side_effect = Exception("Cache error")

        @cached(key_prefix="test", ttl=300)
        async def test_function():
            return {"result": "data"}

        # Should still return function result even if cache fails
        result = await test_function()
        assert result == {"result": "data"}
