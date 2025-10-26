"""
Session Memory Service - Persistent conversation history and context management

This service provides session memory capabilities for multi-day work continuity,
storing conversation history, user interactions, and workspace context.

Features:
- Dual backend support (Redis for speed, SQLite for persistence)
- Conversation history storage and retrieval
- Session persistence across restarts
- Configurable retention policies
- Privacy-preserving local storage

Project Creator: Herman Swanepoel
"""

import json
import logging
import sqlite3
import time
from dataclasses import asdict, dataclass
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

try:
    import redis.asyncio as aioredis

    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    logging.warning("aioredis not available, using SQLite only")


logger = logging.getLogger(__name__)


class StorageBackend(str, Enum):
    """Storage backend types"""

    REDIS = "redis"
    SQLITE = "sqlite"
    HYBRID = "hybrid"  # Redis for hot data, SQLite for cold storage


class MessageType(str, Enum):
    """Types of messages in conversation history"""

    USER_QUERY = "user_query"
    AGENT_RESPONSE = "agent_response"
    SYSTEM_EVENT = "system_event"
    CODE_CONTEXT = "code_context"
    SUGGESTION_ACCEPTED = "suggestion_accepted"
    SUGGESTION_REJECTED = "suggestion_rejected"


@dataclass
class Message:
    """Represents a single message in conversation history"""

    id: str
    session_id: str
    type: MessageType
    content: str
    metadata: Dict[str, Any]
    timestamp: float

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Message":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            session_id=data["session_id"],
            type=MessageType(data["type"]),
            content=data["content"],
            metadata=data.get("metadata", {}),
            timestamp=data["timestamp"],
        )


@dataclass
class Session:
    """Represents a work session"""

    id: str
    workspace_path: str
    created_at: float
    last_accessed: float
    metadata: Dict[str, Any]
    message_count: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Session":
        """Create from dictionary"""
        return cls(
            id=data["id"],
            workspace_path=data["workspace_path"],
            created_at=data["created_at"],
            last_accessed=data["last_accessed"],
            metadata=data.get("metadata", {}),
            message_count=data.get("message_count", 0),
        )


class MemoryConfig:
    """Configuration for memory service"""

    def __init__(
        self,
        backend: StorageBackend = StorageBackend.HYBRID,
        redis_url: str = "redis://localhost:6379",
        sqlite_path: str = "data/sessions/memory.db",
        max_messages_per_session: int = 1000,
        session_ttl_days: int = 30,
        hot_data_ttl_hours: int = 24,
        enable_compression: bool = True,
        enable_encryption: bool = False,
    ):
        self.backend = backend
        self.redis_url = redis_url
        self.sqlite_path = sqlite_path
        self.max_messages_per_session = max_messages_per_session
        self.session_ttl_days = session_ttl_days
        self.hot_data_ttl_hours = hot_data_ttl_hours
        self.enable_compression = enable_compression
        self.enable_encryption = enable_encryption


class MemoryService:
    """
    Session memory service with dual backend support.

    Architecture:
    - Redis: Fast access for recent/hot data (last 24 hours)
    - SQLite: Persistent storage for all data
    - Hybrid mode: Best of both worlds

    Usage:
        config = MemoryConfig(backend=StorageBackend.HYBRID)
        memory = MemoryService(config)
        await memory.initialize()

        # Store interaction
        await memory.store_message(session_id, message)

        # Retrieve context
        history = await memory.get_session_history(session_id, limit=10)
    """

    def __init__(self, config: MemoryConfig):
        self.config = config
        self.redis_client: Optional[aioredis.Redis] = None
        self.sqlite_conn: Optional[sqlite3.Connection] = None
        self.initialized = False

        logger.info(f"MemoryService initialized with backend: {config.backend}")

    async def initialize(self) -> None:
        """Initialize storage backends"""
        if self.initialized:
            return

        try:
            # Initialize SQLite
            await self._init_sqlite()

            # Initialize Redis if available and configured
            if self.config.backend in [StorageBackend.REDIS, StorageBackend.HYBRID]:
                if REDIS_AVAILABLE:
                    await self._init_redis()
                else:
                    logger.warning("Redis not available, falling back to SQLite only")
                    self.config.backend = StorageBackend.SQLITE

            self.initialized = True
            logger.info("MemoryService initialization complete")

        except Exception as e:
            logger.error(f"Failed to initialize MemoryService: {e}")
            raise

    async def _init_sqlite(self) -> None:
        """Initialize SQLite database"""
        db_path = Path(self.config.sqlite_path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.sqlite_conn = sqlite3.connect(str(db_path), check_same_thread=False)

        # Create tables
        cursor = self.sqlite_conn.cursor()

        # Sessions table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS sessions (
                id TEXT PRIMARY KEY,
                workspace_path TEXT NOT NULL,
                created_at REAL NOT NULL,
                last_accessed REAL NOT NULL,
                metadata TEXT,
                message_count INTEGER DEFAULT 0
            )
        """
        )

        # Messages table
        cursor.execute(
            """
            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                session_id TEXT NOT NULL,
                type TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                timestamp REAL NOT NULL,
                FOREIGN KEY (session_id) REFERENCES sessions(id)
            )
        """
        )

        # Create indexes
        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_session_id
            ON messages(session_id)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_messages_timestamp
            ON messages(timestamp)
        """
        )

        cursor.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_sessions_workspace
            ON sessions(workspace_path)
        """
        )

        self.sqlite_conn.commit()
        logger.info("SQLite database initialized")

    async def _init_redis(self) -> None:
        """Initialize Redis connection"""
        try:
            self.redis_client = await aioredis.create_redis_pool(
                self.config.redis_url, encoding="utf-8"
            )

            # Test connection
            await self.redis_client.ping()
            logger.info("Redis connection established")

        except Exception as e:
            logger.error(f"Failed to connect to Redis: {e}")
            self.redis_client = None
            raise

    async def create_session(
        self,
        session_id: str,
        workspace_path: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Session:
        """
        Create a new session.

        Args:
            session_id: Unique session identifier
            workspace_path: Path to workspace
            metadata: Optional session metadata

        Returns:
            Created session object
        """
        now = time.time()
        session = Session(
            id=session_id,
            workspace_path=workspace_path,
            created_at=now,
            last_accessed=now,
            metadata=metadata or {},
            message_count=0,
        )

        # Store in SQLite
        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            """
            INSERT OR REPLACE INTO sessions
            (id, workspace_path, created_at, last_accessed, metadata, message_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                session.id,
                session.workspace_path,
                session.created_at,
                session.last_accessed,
                json.dumps(session.metadata),
                session.message_count,
            ),
        )
        self.sqlite_conn.commit()

        # Store in Redis if available
        if self.redis_client:
            await self.redis_client.setex(
                f"session:{session_id}",
                self.config.hot_data_ttl_hours * 3600,
                json.dumps(session.to_dict()),
            )

        logger.info(f"Created session: {session_id}")
        return session

    async def get_session(self, session_id: str) -> Optional[Session]:
        """
        Retrieve session by ID.

        Args:
            session_id: Session identifier

        Returns:
            Session object or None if not found
        """
        # Try Redis first (hot data)
        if self.redis_client:
            data = await self.redis_client.get(f"session:{session_id}")
            if data:
                return Session.from_dict(json.loads(data))

        # Fall back to SQLite
        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            """
            SELECT id, workspace_path, created_at, last_accessed, metadata, message_count
            FROM sessions WHERE id = ?
        """,  # noqa: E501
            (session_id,),
        )

        row = cursor.fetchone()
        if row:
            return Session(
                id=row[0],
                workspace_path=row[1],
                created_at=row[2],
                last_accessed=row[3],
                metadata=json.loads(row[4]) if row[4] else {},
                message_count=row[5],
            )

        return None

    async def store_message(self, session_id: str, message: Message) -> None:
        """
        Store a message in conversation history.

        Args:
            session_id: Session identifier
            message: Message to store
        """
        # Update session last accessed
        await self._update_session_access(session_id)

        # Store in SQLite (persistent)
        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            """
            INSERT INTO messages (id, session_id, type, content, metadata, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                message.id,
                message.session_id,
                message.type.value,
                message.content,
                json.dumps(message.metadata),
                message.timestamp,
            ),
        )
        self.sqlite_conn.commit()

        # Update message count
        cursor.execute(
            """
            UPDATE sessions SET message_count = message_count + 1
            WHERE id = ?
        """,
            (session_id,),
        )
        self.sqlite_conn.commit()

        # Store in Redis (hot data)
        if self.redis_client:
            # Add to session message list
            await self.redis_client.lpush(
                f"session:{session_id}:messages", json.dumps(message.to_dict())
            )

            # Trim to max size
            await self.redis_client.ltrim(
                f"session:{session_id}:messages",
                0,
                self.config.max_messages_per_session - 1,
            )

            # Set expiry
            await self.redis_client.expire(
                f"session:{session_id}:messages", self.config.hot_data_ttl_hours * 3600
            )

        logger.debug(f"Stored message {message.id} in session {session_id}")

    async def get_session_history(
        self,
        session_id: str,
        limit: int = 50,
        message_types: Optional[List[MessageType]] = None,
    ) -> List[Message]:
        """
        Retrieve conversation history for a session.

        Args:
            session_id: Session identifier
            limit: Maximum number of messages to retrieve
            message_types: Optional filter by message types

        Returns:
            List of messages in chronological order (oldest first)
        """
        messages = []

        # Try Redis first (faster for recent messages)
        if self.redis_client:
            redis_messages = await self.redis_client.lrange(
                f"session:{session_id}:messages", 0, limit - 1
            )

            if redis_messages:
                for msg_json in redis_messages:
                    msg_dict = json.loads(msg_json)
                    message = Message.from_dict(msg_dict)

                    # Filter by type if specified
                    if message_types is None or message.type in message_types:
                        messages.append(message)

                # Redis stores newest first, reverse for chronological order
                messages.reverse()

                if len(messages) >= limit:
                    return messages[:limit]

        # Fall back to SQLite for older messages or if Redis unavailable
        cursor = self.sqlite_conn.cursor()

        type_filter = ""
        params: Tuple = (session_id, limit)

        if message_types:
            type_placeholders = ",".join("?" * len(message_types))
            type_filter = f"AND type IN ({type_placeholders})"
            params = (session_id, *[t.value for t in message_types], limit)

        query = f"""
            SELECT id, session_id, type, content, metadata, timestamp
            FROM messages
            WHERE session_id = ? {type_filter}
            ORDER BY timestamp ASC
            LIMIT ?
        """

        cursor.execute(query, params)
        rows = cursor.fetchall()

        for row in rows:
            message = Message(
                id=row[0],
                session_id=row[1],
                type=MessageType(row[2]),
                content=row[3],
                metadata=json.loads(row[4]) if row[4] else {},
                timestamp=row[5],
            )

            # Avoid duplicates from Redis
            if not any(m.id == message.id for m in messages):
                messages.append(message)

        # Sort chronologically (oldest first)
        messages.sort(key=lambda m: m.timestamp)

        return messages[:limit]

    async def get_recent_context(
        self, session_id: str, time_window_minutes: int = 30
    ) -> List[Message]:
        """
        Get recent messages within a time window for context.

        Args:
            session_id: Session identifier
            time_window_minutes: Time window in minutes

        Returns:
            Recent messages within time window
        """
        cutoff_time = time.time() - (time_window_minutes * 60)

        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            """
            SELECT id, session_id, type, content, metadata, timestamp
            FROM messages
            WHERE session_id = ? AND timestamp >= ?
            ORDER BY timestamp ASC
        """,
            (session_id, cutoff_time),
        )

        messages = []
        for row in cursor.fetchall():
            messages.append(
                Message(
                    id=row[0],
                    session_id=row[1],
                    type=MessageType(row[2]),
                    content=row[3],
                    metadata=json.loads(row[4]) if row[4] else {},
                    timestamp=row[5],
                )
            )

        return messages

    async def persist_session(self, session_id: str) -> bool:
        """
        Explicitly persist session for long-term storage.

        Args:
            session_id: Session identifier

        Returns:
            True if successful
        """
        session = await self.get_session(session_id)
        if not session:
            logger.warning(f"Session {session_id} not found for persistence")
            return False

        # Update metadata to mark as persisted
        session.metadata["persisted"] = True
        session.metadata["persisted_at"] = time.time()

        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            """
            UPDATE sessions SET metadata = ? WHERE id = ?
        """,
            (json.dumps(session.metadata), session_id),
        )
        self.sqlite_conn.commit()

        logger.info(f"Session {session_id} persisted for long-term storage")
        return True

    async def cleanup_old_sessions(self) -> int:
        """
        Clean up sessions older than retention policy.

        Returns:
            Number of sessions cleaned up
        """
        cutoff_time = time.time() - (self.config.session_ttl_days * 86400)

        cursor = self.sqlite_conn.cursor()

        # Find sessions to delete (excluding persisted ones)
        cursor.execute(
            """
            SELECT id FROM sessions
            WHERE last_accessed < ?
            AND (metadata IS NULL OR metadata NOT LIKE '%"persisted": true%')
        """,
            (cutoff_time,),
        )

        session_ids = [row[0] for row in cursor.fetchall()]

        if not session_ids:
            return 0

        # Delete messages
        placeholders = ",".join("?" * len(session_ids))
        cursor.execute(
            f"""
            DELETE FROM messages WHERE session_id IN ({placeholders})
        """,
            session_ids,
        )

        # Delete sessions
        cursor.execute(
            f"""
            DELETE FROM sessions WHERE id IN ({placeholders})
        """,
            session_ids,
        )

        self.sqlite_conn.commit()

        # Clean up Redis
        if self.redis_client:
            for session_id in session_ids:
                await self.redis_client.delete(f"session:{session_id}")
                await self.redis_client.delete(f"session:{session_id}:messages")

        logger.info(f"Cleaned up {len(session_ids)} old sessions")
        return len(session_ids)

    async def get_session_statistics(self, session_id: str) -> Dict[str, Any]:
        """
        Get statistics for a session.

        Args:
            session_id: Session identifier

        Returns:
            Dictionary with session statistics
        """
        cursor = self.sqlite_conn.cursor()

        # Message counts by type
        cursor.execute(
            """
            SELECT type, COUNT(*) as count
            FROM messages
            WHERE session_id = ?
            GROUP BY type
        """,
            (session_id,),
        )

        message_counts = {row[0]: row[1] for row in cursor.fetchall()}

        # Time range
        cursor.execute(
            """
            SELECT MIN(timestamp), MAX(timestamp)
            FROM messages
            WHERE session_id = ?
        """,
            (session_id,),
        )

        time_range = cursor.fetchone()

        # Session info
        session = await self.get_session(session_id)

        return {
            "session_id": session_id,
            "message_counts": message_counts,
            "total_messages": sum(message_counts.values()),
            "first_message": time_range[0] if time_range[0] else None,
            "last_message": time_range[1] if time_range[1] else None,
            "session_duration_hours": (
                (time_range[1] - time_range[0]) / 3600 if time_range[0] and time_range[1] else 0
            ),
            "workspace_path": session.workspace_path if session else None,
            "created_at": session.created_at if session else None,
        }

    async def _update_session_access(self, session_id: str) -> None:
        """Update session last accessed timestamp"""
        now = time.time()

        cursor = self.sqlite_conn.cursor()
        cursor.execute(
            """
            UPDATE sessions SET last_accessed = ? WHERE id = ?
        """,
            (now, session_id),
        )
        self.sqlite_conn.commit()

        # Update Redis cache
        if self.redis_client:
            session_data = await self.redis_client.get(f"session:{session_id}")
            if session_data:
                session_dict = json.loads(session_data)
                session_dict["last_accessed"] = now
                await self.redis_client.setex(
                    f"session:{session_id}",
                    self.config.hot_data_ttl_hours * 3600,
                    json.dumps(session_dict),
                )

    async def close(self) -> None:
        """Close all connections"""
        if self.sqlite_conn:
            self.sqlite_conn.close()
            logger.info("SQLite connection closed")

        if self.redis_client:
            self.redis_client.close()
            await self.redis_client.wait_closed()
            logger.info("Redis connection closed")

        self.initialized = False


# Singleton instance
_memory_service: Optional[MemoryService] = None


async def get_memory_service(config: Optional[MemoryConfig] = None) -> MemoryService:
    """
    Get or create memory service singleton.

    Args:
        config: Optional configuration (used on first call)

    Returns:
        MemoryService instance
    """
    global _memory_service

    if _memory_service is None:
        if config is None:
            config = MemoryConfig()

        _memory_service = MemoryService(config)
        await _memory_service.initialize()

    return _memory_service
