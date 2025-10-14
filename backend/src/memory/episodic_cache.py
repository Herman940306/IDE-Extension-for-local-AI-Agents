"""
Episodic Memory using Redis LRU cache
Project Creator: Herman Swanepoel
"""

import json
import logging
from typing import Any, Optional

import redis

logger = logging.getLogger(__name__)


class EpisodicCache:
    """
    Short-term conversation state using Redis LRU cache.

    Stores recent interactions and context with automatic expiration
    for efficient memory management.
    """

    def __init__(
        self, host: str = "localhost", port: int = 6379, db: int = 0, password: Optional[str] = None
    ):
        """
        Initialize episodic cache.

        Args:
            host: Redis host
            port: Redis port
            db: Redis database number
            password: Optional Redis password
        """
        try:
            self.client = redis.Redis(
                host=host,
                port=port,
                db=db,
                password=password,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            # Test connection
            self.client.ping()
            logger.info(f"EpisodicCache connected to Redis at {host}:{port}")
        except redis.ConnectionError as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    def store(self, key: str, value: Any, ttl: int = 300) -> bool:
        """
        Store value with time-to-live.

        Args:
            key: Cache key
            value: Value to store (will be JSON serialized)
            ttl: Time-to-live in seconds (default 5 minutes)

        Returns:
            True if successful
        """
        try:
            # Serialize value
            if not isinstance(value, str):
                value = json.dumps(value)

            self.client.set(key, value, ex=ttl)
            logger.debug(f"Stored key: {key} with TTL: {ttl}s")
            return True
        except Exception as e:
            logger.error(f"Failed to store key {key}: {e}")
            return False

    def retrieve(self, key: str) -> Optional[Any]:
        """
        Retrieve value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found/expired
        """
        try:
            value = self.client.get(key)
            if value is None:
                logger.debug(f"Cache miss: {key}")
                return None

            # Try to deserialize JSON
            try:
                value = json.loads(value)
            except json.JSONDecodeError:
                pass  # Return as string

            logger.debug(f"Cache hit: {key}")
            return value
        except Exception as e:
            logger.error(f"Failed to retrieve key {key}: {e}")
            return None

    def delete(self, key: str) -> bool:
        """
        Remove key from cache.

        Args:
            key: Cache key

        Returns:
            True if key was deleted
        """
        try:
            result = self.client.delete(key)
            logger.debug(f"Deleted key: {key}")
            return result > 0
        except Exception as e:
            logger.error(f"Failed to delete key {key}: {e}")
            return False

    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            True if key exists
        """
        try:
            return self.client.exists(key) > 0
        except Exception as e:
            logger.error(f"Failed to check key {key}: {e}")
            return False

    def get_ttl(self, key: str) -> int:
        """
        Get remaining TTL for key.

        Args:
            key: Cache key

        Returns:
            Remaining TTL in seconds, -1 if no expiry, -2 if not found
        """
        try:
            return self.client.ttl(key)
        except Exception as e:
            logger.error(f"Failed to get TTL for {key}: {e}")
            return -2

    def extend_ttl(self, key: str, additional_seconds: int) -> bool:
        """
        Extend TTL for existing key.

        Args:
            key: Cache key
            additional_seconds: Seconds to add to current TTL

        Returns:
            True if successful
        """
        try:
            current_ttl = self.get_ttl(key)
            if current_ttl > 0:
                self.client.expire(key, current_ttl + additional_seconds)
                logger.debug(f"Extended TTL for {key} by {additional_seconds}s")
                return True
            return False
        except Exception as e:
            logger.error(f"Failed to extend TTL for {key}: {e}")
            return False

    def clear_all(self) -> bool:
        """
        Clear all keys in current database.

        WARNING: This will delete ALL keys in the Redis database.

        Returns:
            True if successful
        """
        try:
            self.client.flushdb()
            logger.warning("Cleared all keys from Redis database")
            return True
        except Exception as e:
            logger.error(f"Failed to clear database: {e}")
            return False

    def get_stats(self) -> dict:
        """
        Get cache statistics.

        Returns:
            Dict containing cache statistics
        """
        try:
            info = self.client.info("stats")
            return {
                "total_keys": self.client.dbsize(),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
                "hit_rate": (
                    info.get("keyspace_hits", 0)
                    / (info.get("keyspace_hits", 0) + info.get("keyspace_misses", 1))
                ),
            }
        except Exception as e:
            logger.error(f"Failed to get stats: {e}")
            return {}

    def close(self) -> None:
        """Close Redis connection"""
        try:
            self.client.close()
            logger.info("Closed Redis connection")
        except Exception as e:
            logger.error(f"Error closing connection: {e}")
