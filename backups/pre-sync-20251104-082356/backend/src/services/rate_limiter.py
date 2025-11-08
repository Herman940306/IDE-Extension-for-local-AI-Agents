"""
Rate Limiter Service
Project Creator: Herman Swanepoel

Redis-based rate limiter using sliding window algorithm.
"""

import logging
import time
from typing import Optional, Tuple

try:
    from redis.asyncio import Redis
except ImportError:
    Redis = None

logger = logging.getLogger(__name__)


class RateLimiter:
    """Redis-based rate limiter using sliding window"""

    def __init__(
        self,
        redis_client: Optional[Redis],
        default_limit: int = 100,
        default_window: int = 60,
    ) -> None:
        """
        Initialize rate limiter.

        Args:
            redis_client: Async Redis client (None for disabled rate limiting)
            default_limit: Default requests per window
            default_window: Default window in seconds
        """
        self.redis = redis_client
        self.default_limit = default_limit
        self.default_window = default_window
        self._enabled = redis_client is not None

        if not self._enabled:
            logger.warning("Rate limiter disabled: Redis client not provided")
        else:
            logger.info(
                "Rate limiter initialized",
                extra={
                    "default_limit": default_limit,
                    "default_window": default_window,
                },
            )

    async def check_rate_limit(
        self, key: str, limit: Optional[int] = None, window: Optional[int] = None
    ) -> Tuple[bool, int]:
        """
        Check if request is within rate limit.

        Args:
            key: Rate limit key (e.g., client_id, ip_address)
            limit: Request limit (uses default if None)
            window: Time window in seconds (uses default if None)

        Returns:
            Tuple of (allowed: bool, remaining: int)
        """
        # If rate limiting is disabled, allow all requests
        if not self._enabled:
            return (True, -1)

        limit = limit if limit is not None else self.default_limit
        window = window if window is not None else self.default_window

        try:
            now = time.time()
            window_start = now - window

            # Redis key for this rate limit
            redis_key = f"rate_limit:{key}"

            # Use pipeline for atomic operations
            pipe = self.redis.pipeline()

            # Remove expired entries
            pipe.zremrangebyscore(redis_key, 0, window_start)

            # Count current entries
            pipe.zcard(redis_key)

            # Add current request
            pipe.zadd(redis_key, {str(now): now})

            # Set expiration
            pipe.expire(redis_key, window)

            # Execute pipeline
            results = await pipe.execute()

            # Get count (result of ZCARD)
            current_count = results[1]

            # Check if limit exceeded
            allowed = current_count < limit
            remaining = max(0, limit - current_count - 1)

            if not allowed:
                logger.warning(
                    f"Rate limit exceeded for key: {key}",
                    extra={
                        "key": key,
                        "current_count": current_count,
                        "limit": limit,
                        "window": window,
                    },
                )

            return (allowed, remaining)

        except Exception as e:
            logger.error(f"Rate limit check error: {e}", extra={"key": key, "error": str(e)})
            # Fail open: allow request on error
            return (True, -1)

    async def reset(self, key: str) -> bool:
        """
        Reset rate limit for key.

        Args:
            key: Rate limit key to reset

        Returns:
            True if reset successfully, False otherwise
        """
        if not self._enabled:
            return False

        try:
            redis_key = f"rate_limit:{key}"
            await self.redis.delete(redis_key)

            logger.info(f"Rate limit reset for key: {key}", extra={"key": key})

            return True

        except Exception as e:
            logger.error(f"Rate limit reset error: {e}", extra={"key": key, "error": str(e)})
            return False
