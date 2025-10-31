"""
Connection Pool Manager
Project Creator: Herman Swanepoel
"""

from typing import Optional

try:
    from redis.asyncio import ConnectionPool, Redis
except ImportError:
    ConnectionPool = None
    Redis = None


class RedisConnectionPool:
    """Redis connection pool manager"""

    def __init__(self, url: str, max_connections: int = 50, min_idle: int = 10) -> None:
        self.url = url
        self.max_connections = max_connections
        self.pool = (
            ConnectionPool.from_url(url, max_connections=max_connections, decode_responses=True)
            if ConnectionPool
            else None
        )
        self._client: Optional[Redis] = None

    async def get_client(self) -> Optional[Redis]:
        if not self._client and self.pool:
            self._client = Redis(connection_pool=self.pool)
        return self._client

    async def close(self):
        if self._client:
            await self._client.close()
        if self.pool:
            await self.pool.disconnect()
