"""
Response Cache Service
Project Creator: Herman Swanepoel

Redis-based caching layer for LLM responses to reduce duplicate API calls.
"""

import hashlib
import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

try:
    from redis.asyncio import Redis
except ImportError:
    Redis = None

logger = logging.getLogger(__name__)


class ResponseCache:
    """LLM response caching service using Redis"""

    def __init__(
        self,
        redis_client: Optional[Redis],
        default_ttl: int = 3600,
        key_prefix: str = "llm_cache",
    ) -> None:
        """
        Initialize response cache.

        Args:
            redis_client: Async Redis client (None for disabled caching)
            default_ttl: Default TTL in seconds (1 hour)
            key_prefix: Prefix for cache keys
        """
        self.redis = redis_client
        self.default_ttl = default_ttl
        self.key_prefix = key_prefix
        self._stats = {"hits": 0, "misses": 0, "errors": 0}
        self._enabled = redis_client is not None

        if not self._enabled:
            logger.warning("Response cache disabled: Redis client not provided")
        else:
            logger.info(
                "Response cache initialized",
                extra={"default_ttl": default_ttl, "key_prefix": key_prefix},
            )

    async def get(
        self, prompt: str, model: str, context_params: Optional[Dict[str, Any]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Retrieve cached response.

        Args:
            prompt: LLM prompt
            model: Model name
            context_params: Additional context parameters

        Returns:
            Cached response or None if not found
        """
        if not self._enabled:
            return None

        try:
            cache_key = self._generate_cache_key(prompt, model, context_params)

            cached_data = await self.redis.get(cache_key)

            if cached_data:
                self._stats["hits"] += 1
                response = json.loads(cached_data)

                logger.debug(
                    "Cache hit",
                    extra={
                        "cache_key": cache_key[:16] + "...",
                        "model": model,
                        "hit_rate": self._calculate_hit_rate(),
                    },
                )

                return response
            else:
                self._stats["misses"] += 1

                logger.debug(
                    "Cache miss",
                    extra={"cache_key": cache_key[:16] + "...", "model": model},
                )

                return None

        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Cache get error: {e}", extra={"model": model, "error": str(e)})
            return None

    async def set(
        self,
        prompt: str,
        model: str,
        response: Dict[str, Any],
        context_params: Optional[Dict[str, Any]] = None,
        ttl: Optional[int] = None,
    ) -> bool:
        """
        Cache LLM response.

        Args:
            prompt: LLM prompt
            model: Model name
            response: Response to cache
            context_params: Additional context parameters
            ttl: TTL in seconds (uses default if None)

        Returns:
            True if cached successfully, False otherwise
        """
        if not self._enabled:
            return False

        try:
            cache_key = self._generate_cache_key(prompt, model, context_params)
            ttl_seconds = ttl if ttl is not None else self.default_ttl

            # Add metadata to cached response
            cache_data = {
                "response": response,
                "cached_at": datetime.utcnow().isoformat(),
                "model": model,
                "ttl": ttl_seconds,
            }

            await self.redis.setex(cache_key, ttl_seconds, json.dumps(cache_data))

            logger.debug(
                "Response cached",
                extra={
                    "cache_key": cache_key[:16] + "...",
                    "model": model,
                    "ttl": ttl_seconds,
                },
            )

            return True

        except Exception as e:
            self._stats["errors"] += 1
            logger.warning(f"Cache set error: {e}", extra={"model": model, "error": str(e)})
            return False

    def _generate_cache_key(
        self, prompt: str, model: str, context_params: Optional[Dict[str, Any]]
    ) -> str:
        """
        Generate cache key from prompt and parameters.

        Args:
            prompt: LLM prompt
            model: Model name
            context_params: Additional context parameters

        Returns:
            SHA-256 hash as cache key
        """
        # Combine all parameters into a single string
        key_components = [prompt, model]

        if context_params:
            # Sort keys for consistent hashing
            sorted_params = json.dumps(context_params, sort_keys=True)
            key_components.append(sorted_params)

        key_string = "|".join(key_components)

        # Generate SHA-256 hash
        hash_object = hashlib.sha256(key_string.encode())
        hash_hex = hash_object.hexdigest()

        return f"{self.key_prefix}:{hash_hex}"

    def _calculate_hit_rate(self) -> float:
        """Calculate cache hit rate"""
        total = self._stats["hits"] + self._stats["misses"]
        if total == 0:
            return 0.0
        return self._stats["hits"] / total

    async def get_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics.

        Returns:
            Dictionary with cache statistics
        """
        hit_rate = self._calculate_hit_rate()

        return {
            "enabled": self._enabled,
            "hits": self._stats["hits"],
            "misses": self._stats["misses"],
            "errors": self._stats["errors"],
            "hit_rate": hit_rate,
            "total_requests": self._stats["hits"] + self._stats["misses"],
        }

    async def clear(self) -> bool:
        """
        Clear all cached responses.

        Returns:
            True if cleared successfully, False otherwise
        """
        if not self._enabled:
            return False

        try:
            # Find all keys with our prefix
            pattern = f"{self.key_prefix}:*"
            keys = []

            async for key in self.redis.scan_iter(match=pattern):
                keys.append(key)

            if keys:
                await self.redis.delete(*keys)
                logger.info(
                    f"Cache cleared: {len(keys)} keys deleted",
                    extra={"keys_deleted": len(keys)},
                )

            # Reset stats
            self._stats = {"hits": 0, "misses": 0, "errors": 0}

            return True

        except Exception as e:
            logger.error(f"Cache clear error: {e}", extra={"error": str(e)})
            return False
