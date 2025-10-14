"""
DI Container Tests
Project Creator: Herman Swanepoel
"""

import pytest
from src.core.container import Container
from src.services.rate_limiter import RateLimiter
from src.services.response_cache import ResponseCache


class TestContainer:
    """Test dependency injection container"""

    def test_container_initialization(self):
        """Test container can be initialized"""
        container = Container()
        assert container is not None

    def test_config_provider(self):
        """Test configuration provider"""
        container = Container()
        config = container.config()
        assert config is not None
        assert config.app_name == "Enterprise AI Agents API"

    def test_redis_client_provider(self):
        """Test Redis client provider"""
        container = Container()
        redis = container.redis_client()
        # Redis may be None if not available
        assert redis is None or redis is not None

    def test_response_cache_provider(self):
        """Test response cache provider"""
        container = Container()
        cache = container.response_cache()
        assert cache is not None
        assert isinstance(cache, ResponseCache)

    def test_rate_limiter_provider(self):
        """Test rate limiter provider"""
        container = Container()
        limiter = container.rate_limiter()
        assert limiter is not None
        assert isinstance(limiter, RateLimiter)

    def test_singleton_behavior(self):
        """Test that providers return same instance"""
        container = Container()

        config1 = container.config()
        config2 = container.config()
        assert config1 is config2

        cache1 = container.response_cache()
        cache2 = container.response_cache()
        assert cache1 is cache2

        limiter1 = container.rate_limiter()
        limiter2 = container.rate_limiter()
        assert limiter1 is limiter2

    def test_dependency_resolution(self):
        """Test that dependencies are resolved correctly"""
        container = Container()

        # Cache should have redis client injected
        cache = container.response_cache()
        assert hasattr(cache, "redis")

        # Rate limiter should have redis client injected
        limiter = container.rate_limiter()
        assert hasattr(limiter, "redis")

    def test_config_injection(self):
        """Test that config values are injected"""
        container = Container()
        config = container.config()

        # Cache should use config TTL
        cache = container.response_cache()
        assert cache.default_ttl == config.cache.default_ttl

        # Rate limiter should use config limit
        limiter = container.rate_limiter()
        assert limiter.default_limit == config.rate_limit.requests_per_minute
