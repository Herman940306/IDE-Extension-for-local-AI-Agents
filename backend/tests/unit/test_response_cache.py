"""
Unit tests for Response Cache Service

Project Creator: Herman Swanepoel
Date: 2025-10-13
Target Coverage: 90%
"""

import pytest
import json
from src.services.response_cache import ResponseCache


class TestResponseCacheInitialization:
    """Test response cache initialization"""

    def test_initialization_with_redis(self, mock_redis_client):
        """Test cache initialization with Redis client"""
        cache = ResponseCache(
            redis_client=mock_redis_client, default_ttl=3600, key_prefix="test_cache"
        )

        assert cache.redis == mock_redis_client
        assert cache.default_ttl == 3600
        assert cache.key_prefix == "test_cache"
        assert cache._enabled is True

    def test_initialization_without_redis(self):
        """Test cache initialization without Redis client"""
        cache = ResponseCache(redis_client=None)

        assert cache.redis is None
        assert cache._enabled is False

    def test_default_values(self, mock_redis_client):
        """Test default initialization values"""
        cache = ResponseCache(redis_client=mock_redis_client)

        assert cache.default_ttl == 3600
        assert cache.key_prefix == "llm_cache"
        assert cache._stats == {"hits": 0, "misses": 0, "errors": 0}


@pytest.mark.asyncio
class TestResponseCacheGet:
    """Test cache get operations"""

    async def test_get_cache_hit(self, mock_redis_client):
        """Test successful cache hit"""
        cache = ResponseCache(redis_client=mock_redis_client)

        # Mock cached data
        cached_response = {
            "response": {"text": "Cached response"},
            "cached_at": "2025-10-13T10:00:00Z",
            "model": "codellama:7b",
            "ttl": 3600,
        }
        mock_redis_client.get.return_value = json.dumps(cached_response)

        result = await cache.get(prompt="test prompt", model="codellama:7b")

        assert result == cached_response
        assert cache._stats["hits"] == 1
        assert cache._stats["misses"] == 0
        mock_redis_client.get.assert_called_once()

    async def test_get_cache_miss(self, mock_redis_client):
        """Test cache miss"""
        cache = ResponseCache(redis_client=mock_redis_client)

        # Mock no cached data
        mock_redis_client.get.return_value = None

        result = await cache.get(prompt="test prompt", model="codellama:7b")

        assert result is None
        assert cache._stats["hits"] == 0
        assert cache._stats["misses"] == 1

    async def test_get_with_context_params(self, mock_redis_client):
        """Test cache get with context parameters"""
        cache = ResponseCache(redis_client=mock_redis_client)

        cached_response = {"response": {"text": "Test"}}
        mock_redis_client.get.return_value = json.dumps(cached_response)

        result = await cache.get(
            prompt="test prompt",
            model="codellama:7b",
            context_params={"temperature": 0.7, "max_tokens": 100},
        )

        assert result == cached_response
        mock_redis_client.get.assert_called_once()

    async def test_get_when_disabled(self):
        """Test get when cache is disabled"""
        cache = ResponseCache(redis_client=None)

        result = await cache.get(prompt="test prompt", model="codellama:7b")

        assert result is None
        assert cache._stats["hits"] == 0
        assert cache._stats["misses"] == 0

    async def test_get_with_redis_error(self, mock_redis_client):
        """Test get with Redis error"""
        cache = ResponseCache(redis_client=mock_redis_client)

        # Mock Redis error
        mock_redis_client.get.side_effect = Exception("Redis connection error")

        result = await cache.get(prompt="test prompt", model="codellama:7b")

        assert result is None
        assert cache._stats["errors"] == 1


@pytest.mark.asyncio
class TestResponseCacheSet:
    """Test cache set operations"""

    async def test_set_success(self, mock_redis_client):
        """Test successful cache set"""
        cache = ResponseCache(redis_client=mock_redis_client)

        response = {"text": "Test response"}

        result = await cache.set(prompt="test prompt", model="codellama:7b", response=response)

        assert result is True
        mock_redis_client.setex.assert_called_once()

        # Verify the call arguments
        call_args = mock_redis_client.setex.call_args
        assert call_args[0][1] == 3600  # default TTL

        # Verify cached data structure
        cached_data = json.loads(call_args[0][2])
        assert cached_data["response"] == response
        assert cached_data["model"] == "codellama:7b"
        assert "cached_at" in cached_data

    async def test_set_with_custom_ttl(self, mock_redis_client):
        """Test cache set with custom TTL"""
        cache = ResponseCache(redis_client=mock_redis_client)

        response = {"text": "Test response"}

        result = await cache.set(
            prompt="test prompt", model="codellama:7b", response=response, ttl=7200
        )

        assert result is True

        # Verify TTL
        call_args = mock_redis_client.setex.call_args
        assert call_args[0][1] == 7200

    async def test_set_with_context_params(self, mock_redis_client):
        """Test cache set with context parameters"""
        cache = ResponseCache(redis_client=mock_redis_client)

        response = {"text": "Test response"}
        context_params = {"temperature": 0.7}

        result = await cache.set(
            prompt="test prompt",
            model="codellama:7b",
            response=response,
            context_params=context_params,
        )

        assert result is True
        mock_redis_client.setex.assert_called_once()

    async def test_set_when_disabled(self):
        """Test set when cache is disabled"""
        cache = ResponseCache(redis_client=None)

        result = await cache.set(
            prompt="test prompt", model="codellama:7b", response={"text": "Test"}
        )

        assert result is False

    async def test_set_with_redis_error(self, mock_redis_client):
        """Test set with Redis error"""
        cache = ResponseCache(redis_client=mock_redis_client)

        # Mock Redis error
        mock_redis_client.setex.side_effect = Exception("Redis connection error")

        result = await cache.set(
            prompt="test prompt", model="codellama:7b", response={"text": "Test"}
        )

        assert result is False
        assert cache._stats["errors"] == 1


class TestCacheKeyGeneration:
    """Test cache key generation"""

    def test_generate_cache_key_basic(self, mock_redis_client):
        """Test basic cache key generation"""
        cache = ResponseCache(redis_client=mock_redis_client)

        key = cache._generate_cache_key(
            prompt="test prompt", model="codellama:7b", context_params=None
        )

        assert key.startswith("llm_cache:")
        assert len(key) > len("llm_cache:")

    def test_generate_cache_key_with_context(self, mock_redis_client):
        """Test cache key generation with context parameters"""
        cache = ResponseCache(redis_client=mock_redis_client)

        key = cache._generate_cache_key(
            prompt="test prompt",
            model="codellama:7b",
            context_params={"temperature": 0.7},
        )

        assert key.startswith("llm_cache:")

    def test_same_inputs_generate_same_key(self, mock_redis_client):
        """Test that same inputs generate same cache key"""
        cache = ResponseCache(redis_client=mock_redis_client)

        key1 = cache._generate_cache_key(
            prompt="test prompt",
            model="codellama:7b",
            context_params={"temperature": 0.7},
        )

        key2 = cache._generate_cache_key(
            prompt="test prompt",
            model="codellama:7b",
            context_params={"temperature": 0.7},
        )

        assert key1 == key2

    def test_different_inputs_generate_different_keys(self, mock_redis_client):
        """Test that different inputs generate different cache keys"""
        cache = ResponseCache(redis_client=mock_redis_client)

        key1 = cache._generate_cache_key(
            prompt="test prompt 1", model="codellama:7b", context_params=None
        )

        key2 = cache._generate_cache_key(
            prompt="test prompt 2", model="codellama:7b", context_params=None
        )

        assert key1 != key2

    def test_context_param_order_doesnt_matter(self, mock_redis_client):
        """Test that context parameter order doesn't affect key"""
        cache = ResponseCache(redis_client=mock_redis_client)

        key1 = cache._generate_cache_key(
            prompt="test", model="model", context_params={"a": 1, "b": 2}
        )

        key2 = cache._generate_cache_key(
            prompt="test", model="model", context_params={"b": 2, "a": 1}
        )

        assert key1 == key2


class TestCacheStatistics:
    """Test cache statistics"""

    def test_calculate_hit_rate_no_requests(self, mock_redis_client):
        """Test hit rate calculation with no requests"""
        cache = ResponseCache(redis_client=mock_redis_client)

        hit_rate = cache._calculate_hit_rate()

        assert hit_rate == 0.0

    def test_calculate_hit_rate_with_hits(self, mock_redis_client):
        """Test hit rate calculation with hits"""
        cache = ResponseCache(redis_client=mock_redis_client)

        cache._stats["hits"] = 7
        cache._stats["misses"] = 3

        hit_rate = cache._calculate_hit_rate()

        assert hit_rate == 0.7

    def test_calculate_hit_rate_all_hits(self, mock_redis_client):
        """Test hit rate calculation with all hits"""
        cache = ResponseCache(redis_client=mock_redis_client)

        cache._stats["hits"] = 10
        cache._stats["misses"] = 0

        hit_rate = cache._calculate_hit_rate()

        assert hit_rate == 1.0

    @pytest.mark.asyncio
    async def test_get_stats(self, mock_redis_client):
        """Test getting cache statistics"""
        cache = ResponseCache(redis_client=mock_redis_client)

        cache._stats["hits"] = 7
        cache._stats["misses"] = 3
        cache._stats["errors"] = 1

        stats = await cache.get_stats()

        assert stats["enabled"] is True
        assert stats["hits"] == 7
        assert stats["misses"] == 3
        assert stats["errors"] == 1
        assert stats["hit_rate"] == 0.7
        assert stats["total_requests"] == 10

    @pytest.mark.asyncio
    async def test_get_stats_when_disabled(self):
        """Test getting stats when cache is disabled"""
        cache = ResponseCache(redis_client=None)

        stats = await cache.get_stats()

        assert stats["enabled"] is False


@pytest.mark.asyncio
class TestCacheClear:
    """Test cache clear operations"""

    async def test_clear_success(self, mock_redis_client):
        """Test successful cache clear"""
        cache = ResponseCache(redis_client=mock_redis_client)

        # Mock scan_iter to return some keys
        async def mock_scan_iter(match):
            for key in ["llm_cache:key1", "llm_cache:key2"]:
                yield key

        mock_redis_client.scan_iter = mock_scan_iter

        # Set some stats
        cache._stats["hits"] = 10
        cache._stats["misses"] = 5

        result = await cache.clear()

        assert result is True
        mock_redis_client.delete.assert_called_once()

        # Verify stats were reset
        assert cache._stats["hits"] == 0
        assert cache._stats["misses"] == 0
        assert cache._stats["errors"] == 0

    async def test_clear_when_disabled(self):
        """Test clear when cache is disabled"""
        cache = ResponseCache(redis_client=None)

        result = await cache.clear()

        assert result is False

    async def test_clear_with_redis_error(self, mock_redis_client):
        """Test clear with Redis error"""
        cache = ResponseCache(redis_client=mock_redis_client)

        # Mock scan_iter to raise error
        async def mock_scan_iter(match):
            raise Exception("Redis error")
            yield  # Make it a generator

        mock_redis_client.scan_iter = mock_scan_iter

        result = await cache.clear()

        assert result is False

    async def test_clear_with_no_keys(self, mock_redis_client):
        """Test clear when no keys exist"""
        cache = ResponseCache(redis_client=mock_redis_client)

        # Mock scan_iter to return no keys
        async def mock_scan_iter(match):
            return
            yield  # Make it a generator

        mock_redis_client.scan_iter = mock_scan_iter

        result = await cache.clear()

        assert result is True
        # delete should not be called if no keys
        mock_redis_client.delete.assert_not_called()
