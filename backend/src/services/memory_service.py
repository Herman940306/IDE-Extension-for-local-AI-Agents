"""
Session memory service with Redis/SQLite backend
Project Creator: Herman Swanepoel
"""

import logging
import asyncio
import json
import sqlite3
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from pathlib import Path
from abc import ABC, abstractmethod

import aioredis

logger = logging.getLogger(__name__)


class MemoryBackend(ABC):
    """Abstract base class for memory backends"""

    @abstractmethod
    async def store_interaction(self, session_id: str, interaction: Dict[str, Any]) -> None:
        """Store an interaction"""
        pass

    @abstractmethod
    async def get_session_context(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get session context"""
        pass

    @abstractmethod
    async def persist_session(self, session_id: str) -> None:
        """Persist session for long-term storage"""
        pass

    @abstractmethod
    async def restore_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Restore a persisted session"""
        pass

    @abstractmethod
    async def delete_session(self, session_id: str) -> None:
        """Delete a session"""
        pass

    @abstractmethod
    async def cleanup_old_sessions(self, days: int = 7) -> int:
        """Clean up old sessions"""
        pass


class SQLiteMemoryBackend(MemoryBackend):
    """SQLite-based memory backend for development"""

    def __init__(self, db_path: str = "./data/sessions/memory.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize_db()

    def _initialize_db(self) -> None:
        """Initialize SQLite database"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS interactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                timestamp REAL NOT NULL,
                interaction_type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                persisted INTEGER DEFAULT 0
            )
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_session_id 
            ON interactions(session_id)
        """)
        
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_timestamp 
            ON interactions(timestamp)
        """)
        
        conn.commit()
        conn.close()
        logger.info(f"✓ SQLite memory backend initialized: {self.db_path}")

    async def store_interaction(self, session_id: str, interaction: Dict[str, Any]) -> None:
        """Store an interaction in SQLite"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._store_interaction_sync,
            session_id,
            interaction
        )

    def _store_interaction_sync(self, session_id: str, interaction: Dict[str, Any]) -> None:
        """Synchronous store operation"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            INSERT INTO interactions 
            (session_id, timestamp, interaction_type, content, metadata)
            VALUES (?, ?, ?, ?, ?)
        """, (
            session_id,
            interaction.get('timestamp', datetime.now().timestamp()),
            interaction.get('type', 'unknown'),
            json.dumps(interaction.get('content', {})),
            json.dumps(interaction.get('metadata', {}))
        ))
        
        conn.commit()
        conn.close()

    async def get_session_context(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent interactions for a session"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._get_session_context_sync,
            session_id,
            limit
        )

    def _get_session_context_sync(self, session_id: str, limit: int) -> List[Dict[str, Any]]:
        """Synchronous get operation"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT timestamp, interaction_type, content, metadata
            FROM interactions
            WHERE session_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (session_id, limit))
        
        rows = cursor.fetchall()
        conn.close()
        
        interactions = []
        for row in rows:
            interactions.append({
                'timestamp': row[0],
                'type': row[1],
                'content': json.loads(row[2]),
                'metadata': json.loads(row[3])
            })
        
        return list(reversed(interactions))  # Return in chronological order

    async def persist_session(self, session_id: str) -> None:
        """Mark session as persisted"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._persist_session_sync,
            session_id
        )

    def _persist_session_sync(self, session_id: str) -> None:
        """Synchronous persist operation"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            UPDATE interactions
            SET persisted = 1
            WHERE session_id = ?
        """, (session_id,))
        
        conn.commit()
        conn.close()

    async def restore_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Restore a persisted session"""
        return await self.get_session_context(session_id, limit=1000)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session"""
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(
            None,
            self._delete_session_sync,
            session_id
        )

    def _delete_session_sync(self, session_id: str) -> None:
        """Synchronous delete operation"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute("""
            DELETE FROM interactions
            WHERE session_id = ?
        """, (session_id,))
        
        conn.commit()
        conn.close()

    async def cleanup_old_sessions(self, days: int = 7) -> int:
        """Clean up old non-persisted sessions"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self._cleanup_old_sessions_sync,
            days
        )

    def _cleanup_old_sessions_sync(self, days: int) -> int:
        """Synchronous cleanup operation"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cutoff_time = (datetime.now() - timedelta(days=days)).timestamp()
        
        cursor.execute("""
            DELETE FROM interactions
            WHERE timestamp < ? AND persisted = 0
        """, (cutoff_time,))
        
        deleted_count = cursor.rowcount
        conn.commit()
        conn.close()
        
        return deleted_count


class RedisMemoryBackend(MemoryBackend):
    """Redis-based memory backend for production"""

    def __init__(self, redis_url: str = "redis://localhost:6379"):
        self.redis_url = redis_url
        self.redis: Optional[aioredis.Redis] = None

    async def initialize(self) -> None:
        """Initialize Redis connection"""
        try:
            self.redis = await aioredis.create_redis_pool(self.redis_url)
            logger.info("✓ Redis memory backend initialized")
        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            raise

    async def store_interaction(self, session_id: str, interaction: Dict[str, Any]) -> None:
        """Store an interaction in Redis"""
        if not self.redis:
            raise RuntimeError("Redis not initialized")

        key = f"session:{session_id}"
        value = json.dumps(interaction)
        
        # Add to list
        await self.redis.lpush(key, value)
        
        # Set expiration (7 days)
        await self.redis.expire(key, 7 * 24 * 60 * 60)

    async def get_session_context(self, session_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recent interactions for a session"""
        if not self.redis:
            raise RuntimeError("Redis not initialized")

        key = f"session:{session_id}"
        values = await self.redis.lrange(key, 0, limit - 1)
        
        interactions = []
        for value in reversed(values):  # Reverse to get chronological order
            interactions.append(json.loads(value.decode('utf-8')))
        
        return interactions

    async def persist_session(self, session_id: str) -> None:
        """Persist session (remove expiration)"""
        if not self.redis:
            raise RuntimeError("Redis not initialized")

        key = f"session:{session_id}"
        await self.redis.persist(key)

    async def restore_session(self, session_id: str) -> List[Dict[str, Any]]:
        """Restore a persisted session"""
        return await self.get_session_context(session_id, limit=1000)

    async def delete_session(self, session_id: str) -> None:
        """Delete a session"""
        if not self.redis:
            raise RuntimeError("Redis not initialized")

        key = f"session:{session_id}"
        await self.redis.delete(key)

    async def cleanup_old_sessions(self, days: int = 7) -> int:
        """Redis handles expiration automatically"""
        return 0  # Redis auto-expires

    async def close(self) -> None:
        """Close Redis connection"""
        if self.redis:
            self.redis.close()
            await self.redis.wait_closed()


class MemoryService:
    """
    Session memory service for maintaining conversation context
    """

    def __init__(
        self,
        backend: MemoryBackend,
        max_context_length: int = 10
    ):
        """
        Initialize memory service
        
        Args:
            backend: Memory backend (SQLite or Redis)
            max_context_length: Maximum number of interactions to keep in context
        """
        self.backend = backend
        self.max_context_length = max_context_length

    async def store_interaction(
        self,
        session_id: str,
        interaction_type: str,
        content: Dict[str, Any],
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """
        Store an interaction
        
        Args:
            session_id: Session identifier
            interaction_type: Type of interaction (query, response, error, etc.)
            content: Interaction content
            metadata: Additional metadata
        """
        interaction = {
            'timestamp': datetime.now().timestamp(),
            'type': interaction_type,
            'content': content,
            'metadata': metadata or {}
        }
        
        await self.backend.store_interaction(session_id, interaction)
        logger.debug(f"Stored {interaction_type} for session {session_id}")

    async def get_session_context(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Get recent context for a session
        
        Args:
            session_id: Session identifier
            
        Returns:
            List of recent interactions
        """
        return await self.backend.get_session_context(
            session_id,
            limit=self.max_context_length
        )

    async def persist_session(self, session_id: str) -> None:
        """
        Persist session for long-term storage
        
        Args:
            session_id: Session identifier
        """
        await self.backend.persist_session(session_id)
        logger.info(f"Session {session_id} persisted")

    async def restore_session(self, session_id: str) -> List[Dict[str, Any]]:
        """
        Restore a persisted session
        
        Args:
            session_id: Session identifier
            
        Returns:
            All interactions from the session
        """
        interactions = await self.backend.restore_session(session_id)
        logger.info(f"Restored session {session_id} with {len(interactions)} interactions")
        return interactions

    async def delete_session(self, session_id: str) -> None:
        """
        Delete a session
        
        Args:
            session_id: Session identifier
        """
        await self.backend.delete_session(session_id)
        logger.info(f"Deleted session {session_id}")

    async def cleanup_old_sessions(self, days: int = 7) -> int:
        """
        Clean up old sessions
        
        Args:
            days: Delete sessions older than this many days
            
        Returns:
            Number of sessions deleted
        """
        deleted = await self.backend.cleanup_old_sessions(days)
        logger.info(f"Cleaned up {deleted} old sessions")
        return deleted

    def format_context_for_llm(self, interactions: List[Dict[str, Any]]) -> str:
        """
        Format interaction history for LLM context
        
        Args:
            interactions: List of interactions
            
        Returns:
            Formatted context string
        """
        context_parts = []
        
        for interaction in interactions:
            itype = interaction.get('type', 'unknown')
            content = interaction.get('content', {})
            
            if itype == 'query':
                context_parts.append(f"User: {content.get('query', '')}")
            elif itype == 'response':
                context_parts.append(f"Assistant: {content.get('response', '')}")
            elif itype == 'error':
                context_parts.append(f"Error: {content.get('message', '')}")
        
        return "\n".join(context_parts)
