"""
Dependency Injection Container
Project Creator: Herman Swanepoel
"""

from dependency_injector import containers, providers
from src.core.config import get_settings
from src.core.connection_pool import RedisConnectionPool
from src.services.response_cache import ResponseCache
from src.services.rate_limiter import RateLimiter


class Container(containers.DeclarativeContainer):
    """Application dependency injection container"""

    config = providers.Singleton(get_settings)

    redis_pool = providers.Singleton(
        RedisConnectionPool,
        url=config.provided.database.redis_url,
        max_connections=config.provided.database.redis_max_connections,
        min_idle=config.provided.database.redis_min_idle,
    )

    redis_client = providers.Singleton(lambda pool: pool.get_client(), pool=redis_pool)

    # Response Cache
    response_cache = providers.Singleton(
        ResponseCache,
        redis_client=redis_client,
        default_ttl=config.provided.cache.default_ttl,
        key_prefix="llm_cache",
    )

    # Rate Limiter
    rate_limiter = providers.Singleton(
        RateLimiter,
        redis_client=redis_client,
        default_limit=config.provided.rate_limit.requests_per_minute,
        default_window=60,
    )
