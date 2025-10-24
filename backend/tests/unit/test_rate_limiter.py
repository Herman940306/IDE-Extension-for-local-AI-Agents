"""
Unit tests for Rate Limiter Service

Project Creator: Herman Swanepoel
Date: 2025-10-13
Target Coverage: 90%
"""

from unittest.mock import AsyncMock, MagicMock

import pytest
from src.services.rate_limiter import RateLimiter


class TestRateLimiterInitialization:
    """Test rate limiter initialization"""

    def test_initialization_with_redis(self, mock_redis_client):
        """Test rate limiter initialization with Redis client"""
        limiter = RateLimiter(redis_client=mock_redis_client, default_limit=100, default_window=60)

        assert limiter.redis == mock_redis_client
        assert limiter.default_limit == 100
        assert limiter.default_window == 60
        assert limiter._enabled is True

    def test_initialization_without_redis(self):
        """Test rate limiter initialization without Redis client"""
        limiter = RateLimiter(redis_client=None)

        assert limiter.redis is None
        assert limiter._enabled is False

    def test_default_values(self, mock_redis_client):
        """Test default initialization values"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        assert limiter.default_limit == 100
        assert limiter.default_window == 60


@pytest.mark.asyncio
class TestRateLimiterCheck:
    """Test rate limit checking"""

    async def test_check_within_limit(self, mock_redis_client):
        """Test check when within rate limit"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(
            return_value=[
                None,  # zremrangebyscore result
                5,  # zcard result (current count)
                None,  # zadd result
                None,  # expire result
            ]
        )
        mock_redis_client.pipeline.return_value = mock_pipeline

        allowed, remaining = await limiter.check_rate_limit(key="test_client", limit=100, window=60)

        assert allowed is True
        assert remaining == 94  # 100 - 5 - 1

    async def test_check_at_limit(self, mock_redis_client):
        """Test check when at rate limit"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(
            return_value=[
                None,  # zremrangebyscore result
                100,  # zcard result (at limit)
                None,  # zadd result
                None,  # expire result
            ]
        )
        mock_redis_client.pipeline.return_value = mock_pipeline

        allowed, remaining = await limiter.check_rate_limit(key="test_client", limit=100, window=60)

        assert allowed is False
        assert remaining == 0

    async def test_check_exceeded_limit(self, mock_redis_client):
        """Test check when rate limit exceeded"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(
            return_value=[
                None,  # zremrangebyscore result
                105,  # zcard result (exceeded)
                None,  # zadd result
                None,  # expire result
            ]
        )
        mock_redis_client.pipeline.return_value = mock_pipeline

        allowed, remaining = await limiter.check_rate_limit(key="test_client", limit=100, window=60)

        assert allowed is False
        assert remaining == 0

    async def test_check_with_default_params(self, mock_redis_client):
        """Test check with default limit and window"""
        limiter = RateLimiter(redis_client=mock_redis_client, default_limit=50, default_window=30)

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(return_value=[None, 10, None, None])
        mock_redis_client.pipeline.return_value = mock_pipeline

        allowed, remaining = await limiter.check_rate_limit(key="test_client")

        assert allowed is True
        assert remaining == 39  # 50 - 10 - 1

    async def test_check_when_disabled(self):
        """Test check when rate limiter is disabled"""
        limiter = RateLimiter(redis_client=None)

        allowed, remaining = await limiter.check_rate_limit(key="test_client", limit=100, window=60)

        assert allowed is True
        assert remaining == -1

    async def test_check_with_redis_error(self, mock_redis_client):
        """Test check with Redis error (fail open)"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        # Mock Redis error
        mock_redis_client.pipeline.side_effect = Exception("Redis connection error")

        allowed, remaining = await limiter.check_rate_limit(key="test_client", limit=100, window=60)

        # Should fail open (allow request)
        assert allowed is True
        assert remaining == -1

    async def test_check_uses_correct_redis_key(self, mock_redis_client):
        """Test that correct Redis key is used"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(return_value=[None, 5, None, None])
        mock_pipeline.zremrangebyscore = MagicMock()
        mock_redis_client.pipeline.return_value = mock_pipeline

        await limiter.check_rate_limit(key="client_123", limit=100, window=60)

        # Verify the Redis key format
        mock_pipeline.zremrangebyscore.assert_called_once()
        call_args = mock_pipeline.zremrangebyscore.call_args[0]
        assert call_args[0] == "rate_limit:client_123"

    async def test_check_multiple_clients(self, mock_redis_client):
        """Test rate limiting for multiple clients"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        # Mock pipeline for different clients
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(return_value=[None, 5, None, None])
        mock_redis_client.pipeline.return_value = mock_pipeline

        # Check for client 1
        allowed1, remaining1 = await limiter.check_rate_limit(key="client_1", limit=100, window=60)

        # Check for client 2
        allowed2, remaining2 = await limiter.check_rate_limit(key="client_2", limit=100, window=60)

        assert allowed1 is True
        assert allowed2 is True


@pytest.mark.asyncio
class TestRateLimiterReset:
    """Test rate limiter reset"""

    async def test_reset_success(self, mock_redis_client):
        """Test successful rate limit reset"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        mock_redis_client.delete = AsyncMock(return_value=1)

        result = await limiter.reset(key="test_client")

        assert result is True
        mock_redis_client.delete.assert_called_once_with("rate_limit:test_client")

    async def test_reset_when_disabled(self):
        """Test reset when rate limiter is disabled"""
        limiter = RateLimiter(redis_client=None)

        result = await limiter.reset(key="test_client")

        assert result is False

    async def test_reset_with_redis_error(self, mock_redis_client):
        """Test reset with Redis error"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        # Mock Redis error
        mock_redis_client.delete = AsyncMock(side_effect=Exception("Redis error"))

        result = await limiter.reset(key="test_client")

        assert result is False

    async def test_reset_multiple_clients(self, mock_redis_client):
        """Test resetting multiple clients"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        mock_redis_client.delete = AsyncMock(return_value=1)

        result1 = await limiter.reset(key="client_1")
        result2 = await limiter.reset(key="client_2")

        assert result1 is True
        assert result2 is True
        assert mock_redis_client.delete.call_count == 2


class TestRateLimiterEdgeCases:
    """Test edge cases"""

    @pytest.mark.asyncio
    async def test_zero_limit(self, mock_redis_client):
        """Test with zero limit"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(return_value=[None, 0, None, None])
        mock_redis_client.pipeline.return_value = mock_pipeline

        allowed, remaining = await limiter.check_rate_limit(key="test_client", limit=0, window=60)

        assert allowed is False
        assert remaining == 0

    @pytest.mark.asyncio
    async def test_very_large_limit(self, mock_redis_client):
        """Test with very large limit"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(return_value=[None, 100, None, None])
        mock_redis_client.pipeline.return_value = mock_pipeline

        allowed, remaining = await limiter.check_rate_limit(
            key="test_client", limit=1000000, window=60
        )

        assert allowed is True
        assert remaining == 999899  # 1000000 - 100 - 1

    @pytest.mark.asyncio
    async def test_very_short_window(self, mock_redis_client):
        """Test with very short time window"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(return_value=[None, 5, None, None])
        mock_redis_client.pipeline.return_value = mock_pipeline

        allowed, remaining = await limiter.check_rate_limit(
            key="test_client", limit=100, window=1  # 1 second window
        )

        assert allowed is True

    @pytest.mark.asyncio
    async def test_very_long_window(self, mock_redis_client):
        """Test with very long time window"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        # Mock pipeline
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(return_value=[None, 5, None, None])
        mock_redis_client.pipeline.return_value = mock_pipeline

        allowed, remaining = await limiter.check_rate_limit(
            key="test_client", limit=100, window=86400  # 24 hours
        )

        assert allowed is True


class TestRateLimiterIntegration:
    """Test rate limiter integration scenarios"""

    @pytest.mark.asyncio
    async def test_sequential_requests(self, mock_redis_client):
        """Test sequential requests incrementing count"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        # Mock pipeline with increasing counts
        counts = [5, 6, 7, 8]

        for count in counts:
            mock_pipeline = AsyncMock()
            mock_pipeline.execute = AsyncMock(return_value=[None, count, None, None])
            mock_redis_client.pipeline.return_value = mock_pipeline

            allowed, remaining = await limiter.check_rate_limit(
                key="test_client", limit=100, window=60
            )

            assert allowed is True
            assert remaining == 100 - count - 1

    @pytest.mark.asyncio
    async def test_reset_and_recheck(self, mock_redis_client):
        """Test reset followed by recheck"""
        limiter = RateLimiter(redis_client=mock_redis_client)

        # First check - at limit
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(return_value=[None, 100, None, None])
        mock_redis_client.pipeline.return_value = mock_pipeline

        allowed, remaining = await limiter.check_rate_limit(key="test_client", limit=100, window=60)

        assert allowed is False

        # Reset
        mock_redis_client.delete = AsyncMock(return_value=1)
        reset_result = await limiter.reset(key="test_client")
        assert reset_result is True

        # Check again - should be allowed
        mock_pipeline = AsyncMock()
        mock_pipeline.execute = AsyncMock(return_value=[None, 0, None, None])
        mock_redis_client.pipeline.return_value = mock_pipeline

        allowed, remaining = await limiter.check_rate_limit(key="test_client", limit=100, window=60)

        assert allowed is True
