"""
Dependency Injection Container
Project Creator: Herman Swanepoel
"""

from dependency_injector import containers, providers
from src.core.config import get_settings
from src.services.response_cache import ResponseCache
from src.services.rate_limiter import RateLimiter

try:
    from redis.asyncio import Redis
except ImportError:
    Redis = None


class Container(containers.DeclarativeContainer):
    """Application dependency injection container"""

    # Configuration
    config = providers.Singleton(get_settings)

    # Redis connection
    redis_client = providers.Singleton(
        lambda cfg: (
            Redis.from_url(
                cfg.database.redis_url,
                encoding="utf-8",
                decode_responses=True,
                max_connections=cfg.database.redis_max_connections,
            )
            if Redis
            else None
        ),
        cfg=config,
    )

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
