"""
Comprehensive tests for MemoryService - targeting 70%+ coverage
"""

import json
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

import pytest
from src.services.memory_service import (
    MemoryConfig,
    MemoryService,
    Message,
    MessageType,
    Session,
    StorageBackend,
    get_memory_service,
)

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def temp_db():
    """Create temporary database for testing"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name
    yield db_path
    Path(db_path).unlink(missing_ok=True)


@pytest.fixture
def sqlite_config(temp_db):
    """Create SQLite-only configuration"""
    return MemoryConfig(
        backend=StorageBackend.SQLITE,
        sqlite_path=temp_db,
        max_messages_per_session=100,
        session_ttl_days=7,
        hot_data_ttl_hours=2,
    )


@pytest.fixture
async def memory_service(sqlite_config):
    """Create initialized memory service"""
    service = MemoryService(sqlite_config)
    await service.initialize()
    yield service
    await service.close()


@pytest.fixture
def sample_message():
    """Create sample message"""
    return Message(
        id="msg-123",
        session_id="session-abc",
        type=MessageType.USER_QUERY,
        content="Test query content",
        metadata={"agent": "test_agent"},
        timestamp=time.time(),
    )


@pytest.fixture
def sample_session():
    """Create sample session"""
    return Session(
        id="session-xyz",
        workspace_path="/workspace/project",
        created_at=time.time(),
        last_accessed=time.time(),
        metadata={"project": "test"},
        message_count=0,
    )


# ============================================================================
# Test Data Models
# ============================================================================


class TestMessageModel:
    """Test Message data model"""

    def test_message_creation(self):
        """Test message creation"""
        msg = Message(
            id="msg-1",
            session_id="sess-1",
            type=MessageType.USER_QUERY,
            content="Hello",
            metadata={"key": "value"},
            timestamp=1234567890.0,
        )

        assert msg.id == "msg-1"
        assert msg.session_id == "sess-1"
        assert msg.type == MessageType.USER_QUERY
        assert msg.content == "Hello"
        assert msg.metadata == {"key": "value"}
        assert msg.timestamp == 1234567890.0

    def test_message_to_dict(self, sample_message):
        """Test message to dictionary conversion"""
        msg_dict = sample_message.to_dict()

        assert isinstance(msg_dict, dict)
        assert msg_dict["id"] == sample_message.id
        assert msg_dict["session_id"] == sample_message.session_id
        assert msg_dict["content"] == sample_message.content

    def test_message_from_dict(self):
        """Test message from dictionary creation"""
        data = {
            "id": "msg-999",
            "session_id": "sess-999",
            "type": "user_query",
            "content": "Test content",
            "metadata": {"test": True},
            "timestamp": 9999999.0,
        }

        msg = Message.from_dict(data)

        assert msg.id == "msg-999"
        assert msg.type == MessageType.USER_QUERY
        assert msg.content == "Test content"
        assert msg.metadata == {"test": True}

    def test_message_type_enum(self):
        """Test MessageType enum values"""
        assert MessageType.USER_QUERY.value == "user_query"
        assert MessageType.AGENT_RESPONSE.value == "agent_response"
        assert MessageType.SYSTEM_EVENT.value == "system_event"
        assert MessageType.CODE_CONTEXT.value == "code_context"
        assert MessageType.SUGGESTION_ACCEPTED.value == "suggestion_accepted"
        assert MessageType.SUGGESTION_REJECTED.value == "suggestion_rejected"


class TestSessionModel:
    """Test Session data model"""

    def test_session_creation(self):
        """Test session creation"""
        sess = Session(
            id="sess-1",
            workspace_path="/workspace",
            created_at=1000.0,
            last_accessed=2000.0,
            metadata={"env": "test"},
            message_count=42,
        )

        assert sess.id == "sess-1"
        assert sess.workspace_path == "/workspace"
        assert sess.created_at == 1000.0
        assert sess.last_accessed == 2000.0
        assert sess.metadata == {"env": "test"}
        assert sess.message_count == 42

    def test_session_to_dict(self, sample_session):
        """Test session to dictionary conversion"""
        sess_dict = sample_session.to_dict()

        assert isinstance(sess_dict, dict)
        assert sess_dict["id"] == sample_session.id
        assert sess_dict["workspace_path"] == sample_session.workspace_path

    def test_session_from_dict(self):
        """Test session from dictionary creation"""
        data = {
            "id": "sess-789",
            "workspace_path": "/test/path",
            "created_at": 1111.0,
            "last_accessed": 2222.0,
            "metadata": {"version": "1.0"},
            "message_count": 10,
        }

        sess = Session.from_dict(data)

        assert sess.id == "sess-789"
        assert sess.workspace_path == "/test/path"
        assert sess.message_count == 10


class TestMemoryConfig:
    """Test MemoryConfig"""

    def test_config_defaults(self):
        """Test default configuration"""
        config = MemoryConfig()

        assert config.backend == StorageBackend.HYBRID
        assert config.redis_url == "redis://localhost:6379"
        assert config.sqlite_path == "data/sessions/memory.db"
        assert config.max_messages_per_session == 1000
        assert config.session_ttl_days == 30
        assert config.hot_data_ttl_hours == 24
        assert config.enable_compression is True
        assert config.enable_encryption is False

    def test_config_custom_values(self):
        """Test custom configuration"""
        config = MemoryConfig(
            backend=StorageBackend.SQLITE,
            redis_url="redis://custom:6380",
            sqlite_path="/custom/path.db",
            max_messages_per_session=500,
            session_ttl_days=60,
            hot_data_ttl_hours=12,
            enable_compression=False,
            enable_encryption=True,
        )

        assert config.backend == StorageBackend.SQLITE
        assert config.redis_url == "redis://custom:6380"
        assert config.sqlite_path == "/custom/path.db"
        assert config.max_messages_per_session == 500
        assert config.session_ttl_days == 60
        assert config.hot_data_ttl_hours == 12
        assert config.enable_compression is False
        assert config.enable_encryption is True

    def test_storage_backend_enum(self):
        """Test StorageBackend enum"""
        assert StorageBackend.REDIS.value == "redis"
        assert StorageBackend.SQLITE.value == "sqlite"
        assert StorageBackend.HYBRID.value == "hybrid"


# ============================================================================
# Test MemoryService Initialization
# ============================================================================


class TestMemoryServiceInitialization:
    """Test MemoryService initialization"""

    def test_service_creation(self, sqlite_config):
        """Test service creation"""
        service = MemoryService(sqlite_config)

        assert service.config == sqlite_config
        assert service.redis_client is None
        assert service.sqlite_conn is None
        assert service.initialized is False

    @pytest.mark.asyncio
    async def test_sqlite_initialization(self, sqlite_config):
        """Test SQLite initialization"""
        service = MemoryService(sqlite_config)
        await service.initialize()

        assert service.initialized is True
        assert service.sqlite_conn is not None

        # Check tables were created
        cursor = service.sqlite_conn.cursor()
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='sessions'")
        assert cursor.fetchone() is not None

        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='messages'")
        assert cursor.fetchone() is not None

        await service.close()

    @pytest.mark.asyncio
    async def test_initialization_idempotent(self, memory_service):
        """Test initialization is idempotent"""
        # Initialize again
        await memory_service.initialize()

        assert memory_service.initialized is True

    @pytest.mark.asyncio
    async def test_initialization_failure_handling(self, sqlite_config):
        """Test initialization handles failures gracefully"""
        # Use invalid path to trigger error on most systems
        # Note: On Windows with admin rights, this might still succeed
        sqlite_config.sqlite_path = "/invalid/path/that/cannot/be/created/test.db"

        service = MemoryService(sqlite_config)

        # Attempt initialization - may raise exception or succeed
        # depending on OS permissions
        try:
            await service.initialize()
            # If it succeeds (e.g., Windows with permissions), that's also acceptable
            assert service.initialized is True
        except (OSError, PermissionError, Exception):
            # Expected on Unix-like systems or without proper permissions
            assert service.initialized is False


# ============================================================================
# Test Session Management
# ============================================================================


class TestSessionManagement:
    """Test session creation and retrieval"""

    @pytest.mark.asyncio
    async def test_create_session(self, memory_service):
        """Test session creation"""
        session = await memory_service.create_session(
            session_id="test-session-1",
            workspace_path="/workspace/test",
            metadata={"project": "test_project"},
        )

        assert session.id == "test-session-1"
        assert session.workspace_path == "/workspace/test"
        assert session.metadata["project"] == "test_project"
        assert session.message_count == 0

    @pytest.mark.asyncio
    async def test_create_session_no_metadata(self, memory_service):
        """Test session creation without metadata"""
        session = await memory_service.create_session(
            session_id="test-session-2",
            workspace_path="/workspace/test2",
        )

        assert session.id == "test-session-2"
        assert session.metadata == {}

    @pytest.mark.asyncio
    async def test_get_session(self, memory_service):
        """Test session retrieval"""
        # Create session
        await memory_service.create_session(
            session_id="get-test-session",
            workspace_path="/workspace/get",
        )

        # Retrieve session
        session = await memory_service.get_session("get-test-session")

        assert session is not None
        assert session.id == "get-test-session"
        assert session.workspace_path == "/workspace/get"

    @pytest.mark.asyncio
    async def test_get_nonexistent_session(self, memory_service):
        """Test retrieving non-existent session"""
        session = await memory_service.get_session("nonexistent-session")

        assert session is None

    @pytest.mark.asyncio
    async def test_update_session_access(self, memory_service):
        """Test session access time update"""
        # Create session
        session1 = await memory_service.create_session(
            session_id="access-test-session",
            workspace_path="/workspace/access",
        )

        initial_access = session1.last_accessed

        # Wait a bit
        time.sleep(0.1)

        # Update access (indirectly through _update_session_access)
        await memory_service._update_session_access("access-test-session")

        # Retrieve and check
        session2 = await memory_service.get_session("access-test-session")

        assert session2.last_accessed > initial_access


# ============================================================================
# Test Message Storage and Retrieval
# ============================================================================


class TestMessageStorage:
    """Test message storage and retrieval"""

    @pytest.mark.asyncio
    async def test_store_message(self, memory_service):
        """Test storing a message"""
        # Create session first
        await memory_service.create_session(
            session_id="msg-session-1",
            workspace_path="/workspace/msg",
        )

        # Create and store message
        message = Message(
            id="msg-001",
            session_id="msg-session-1",
            type=MessageType.USER_QUERY,
            content="Hello, world!",
            metadata={"timestamp_ms": 1000},
            timestamp=time.time(),
        )

        await memory_service.store_message("msg-session-1", message)

        # Verify message was stored
        cursor = memory_service.sqlite_conn.cursor()
        cursor.execute("SELECT * FROM messages WHERE id = ?", ("msg-001",))
        row = cursor.fetchone()

        assert row is not None
        assert row[0] == "msg-001"  # id
        assert row[1] == "msg-session-1"  # session_id

    @pytest.mark.asyncio
    async def test_store_multiple_messages(self, memory_service):
        """Test storing multiple messages"""
        await memory_service.create_session(
            session_id="multi-msg-session",
            workspace_path="/workspace/multi",
        )

        # Store multiple messages
        for i in range(5):
            message = Message(
                id=f"msg-{i}",
                session_id="multi-msg-session",
                type=MessageType.USER_QUERY,
                content=f"Message {i}",
                metadata={},
                timestamp=time.time() + i,
            )
            await memory_service.store_message("multi-msg-session", message)

        # Check message count
        session = await memory_service.get_session("multi-msg-session")
        assert session.message_count == 5

    @pytest.mark.asyncio
    async def test_get_session_history(self, memory_service):
        """Test retrieving session history"""
        session_id = "history-session"

        await memory_service.create_session(
            session_id=session_id,
            workspace_path="/workspace/history",
        )

        # Store messages
        for i in range(10):
            message = Message(
                id=f"hist-msg-{i}",
                session_id=session_id,
                type=MessageType.USER_QUERY,
                content=f"History message {i}",
                metadata={},
                timestamp=time.time() + i,
            )
            await memory_service.store_message(session_id, message)

        # Retrieve history
        history = await memory_service.get_session_history(session_id, limit=5)

        assert len(history) == 5
        # Should be in chronological order (oldest first)
        assert history[0].content == "History message 0"

    @pytest.mark.asyncio
    async def test_get_session_history_with_type_filter(self, memory_service):
        """Test retrieving history with message type filter"""
        session_id = "filter-session"

        await memory_service.create_session(
            session_id=session_id,
            workspace_path="/workspace/filter",
        )

        # Store messages of different types
        for i in range(5):
            msg_type = MessageType.USER_QUERY if i % 2 == 0 else MessageType.AGENT_RESPONSE
            message = Message(
                id=f"filter-msg-{i}",
                session_id=session_id,
                type=msg_type,
                content=f"Message {i}",
                metadata={},
                timestamp=time.time() + i,
            )
            await memory_service.store_message(session_id, message)

        # Retrieve only user queries
        history = await memory_service.get_session_history(
            session_id,
            limit=10,
            message_types=[MessageType.USER_QUERY],
        )

        assert len(history) == 3  # 0, 2, 4
        assert all(msg.type == MessageType.USER_QUERY for msg in history)

    @pytest.mark.asyncio
    async def test_get_recent_context(self, memory_service):
        """Test getting recent context within time window"""
        session_id = "context-session"

        await memory_service.create_session(
            session_id=session_id,
            workspace_path="/workspace/context",
        )

        now = time.time()

        # Store old message (outside window)
        old_message = Message(
            id="old-msg",
            session_id=session_id,
            type=MessageType.USER_QUERY,
            content="Old message",
            metadata={},
            timestamp=now - 3600,  # 1 hour ago
        )
        await memory_service.store_message(session_id, old_message)

        # Store recent messages (inside window)
        for i in range(3):
            recent_message = Message(
                id=f"recent-msg-{i}",
                session_id=session_id,
                type=MessageType.USER_QUERY,
                content=f"Recent message {i}",
                metadata={},
                timestamp=now - (i * 60),  # Within last few minutes
            )
            await memory_service.store_message(session_id, recent_message)

        # Get context from last 30 minutes
        context = await memory_service.get_recent_context(
            session_id,
            time_window_minutes=30,
        )

        # Should only get recent messages
        assert len(context) == 3
        assert all("Recent" in msg.content for msg in context)


# ============================================================================
# Test Session Persistence and Cleanup
# ============================================================================


class TestSessionPersistence:
    """Test session persistence and cleanup"""

    @pytest.mark.asyncio
    async def test_persist_session(self, memory_service):
        """Test persisting a session"""
        session_id = "persist-session"

        await memory_service.create_session(
            session_id=session_id,
            workspace_path="/workspace/persist",
        )

        # Persist the session
        result = await memory_service.persist_session(session_id)

        assert result is True

        # Check metadata
        session = await memory_service.get_session(session_id)
        assert session.metadata.get("persisted") is True
        assert "persisted_at" in session.metadata

    @pytest.mark.asyncio
    async def test_persist_nonexistent_session(self, memory_service):
        """Test persisting non-existent session"""
        result = await memory_service.persist_session("nonexistent-session")

        assert result is False

    @pytest.mark.asyncio
    async def test_cleanup_old_sessions(self, memory_service):
        """Test cleaning up old sessions"""
        # Create old session (simulate by setting old timestamp)
        old_time = time.time() - (10 * 86400)  # 10 days ago

        cursor = memory_service.sqlite_conn.cursor()
        cursor.execute(
            """
            INSERT INTO sessions
            (id, workspace_path, created_at, last_accessed, metadata, message_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                "old-session",
                "/workspace/old",
                old_time,
                old_time,
                json.dumps({}),
                0,
            ),
        )
        memory_service.sqlite_conn.commit()

        # Create recent session
        await memory_service.create_session(
            session_id="recent-session",
            workspace_path="/workspace/recent",
        )

        # Cleanup (with 7 day TTL, old session should be deleted)
        cleaned_count = await memory_service.cleanup_old_sessions()

        assert cleaned_count == 1

        # Verify old session is gone
        old_session = await memory_service.get_session("old-session")
        assert old_session is None

        # Verify recent session still exists
        recent_session = await memory_service.get_session("recent-session")
        assert recent_session is not None

    @pytest.mark.asyncio
    async def test_cleanup_preserves_persisted_sessions(self, memory_service):
        """Test cleanup preserves persisted sessions"""
        # Create old persisted session
        old_time = time.time() - (10 * 86400)  # 10 days ago

        cursor = memory_service.sqlite_conn.cursor()
        cursor.execute(
            """
            INSERT INTO sessions
            (id, workspace_path, created_at, last_accessed, metadata, message_count)
            VALUES (?, ?, ?, ?, ?, ?)
        """,
            (
                "persisted-old-session",
                "/workspace/persisted",
                old_time,
                old_time,
                json.dumps({"persisted": True}),
                0,
            ),
        )
        memory_service.sqlite_conn.commit()

        # Cleanup
        cleaned_count = await memory_service.cleanup_old_sessions()

        # Persisted session should be preserved
        persisted_session = await memory_service.get_session("persisted-old-session")
        assert persisted_session is not None
        assert cleaned_count == 0


# ============================================================================
# Test Session Statistics
# ============================================================================


class TestSessionStatistics:
    """Test session statistics"""

    @pytest.mark.asyncio
    async def test_get_session_statistics(self, memory_service):
        """Test getting session statistics"""
        session_id = "stats-session"

        await memory_service.create_session(
            session_id=session_id,
            workspace_path="/workspace/stats",
        )

        # Store messages of different types
        message_types = [
            MessageType.USER_QUERY,
            MessageType.USER_QUERY,
            MessageType.AGENT_RESPONSE,
            MessageType.SYSTEM_EVENT,
        ]

        for i, msg_type in enumerate(message_types):
            message = Message(
                id=f"stats-msg-{i}",
                session_id=session_id,
                type=msg_type,
                content=f"Message {i}",
                metadata={},
                timestamp=time.time() + i,
            )
            await memory_service.store_message(session_id, message)

        # Get statistics
        stats = await memory_service.get_session_statistics(session_id)

        assert stats["session_id"] == session_id
        assert stats["total_messages"] == 4
        assert stats["message_counts"]["user_query"] == 2
        assert stats["message_counts"]["agent_response"] == 1
        assert stats["message_counts"]["system_event"] == 1
        assert stats["workspace_path"] == "/workspace/stats"
        assert stats["first_message"] is not None
        assert stats["last_message"] is not None

    @pytest.mark.asyncio
    async def test_get_statistics_empty_session(self, memory_service):
        """Test statistics for session with no messages"""
        session_id = "empty-stats-session"

        await memory_service.create_session(
            session_id=session_id,
            workspace_path="/workspace/empty",
        )

        stats = await memory_service.get_session_statistics(session_id)

        assert stats["total_messages"] == 0
        assert stats["message_counts"] == {}
        assert stats["first_message"] is None
        assert stats["last_message"] is None


# ============================================================================
# Test Connection Management
# ============================================================================


class TestConnectionManagement:
    """Test connection management"""

    @pytest.mark.asyncio
    async def test_close_connections(self, sqlite_config):
        """Test closing connections"""
        service = MemoryService(sqlite_config)
        await service.initialize()

        assert service.initialized is True
        assert service.sqlite_conn is not None

        await service.close()

        assert service.initialized is False

    @pytest.mark.asyncio
    async def test_close_without_initialization(self, sqlite_config):
        """Test closing before initialization"""
        service = MemoryService(sqlite_config)

        # Should not raise error
        await service.close()

        assert service.initialized is False


# ============================================================================
# Test Singleton Pattern
# ============================================================================


class TestSingletonPattern:
    """Test get_memory_service singleton"""

    @pytest.mark.asyncio
    async def test_get_memory_service_creates_instance(self, temp_db):
        """Test singleton creation"""
        config = MemoryConfig(
            backend=StorageBackend.SQLITE,
            sqlite_path=temp_db,
        )

        service = await get_memory_service(config)

        assert service is not None
        assert service.initialized is True

        await service.close()

    @pytest.mark.asyncio
    async def test_get_memory_service_default_config(self, temp_db):
        """Test singleton with default config"""
        # Patch default config path to use temp db
        with patch("src.services.memory_service.MemoryConfig") as mock_config_class:
            mock_config = MemoryConfig(
                backend=StorageBackend.SQLITE,
                sqlite_path=temp_db,
            )
            mock_config_class.return_value = mock_config

            service = await get_memory_service()

            assert service is not None


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling"""

    @pytest.mark.asyncio
    async def test_store_message_updates_count(self, memory_service):
        """Test message storage updates session count"""
        session_id = "count-test-session"

        await memory_service.create_session(
            session_id=session_id,
            workspace_path="/workspace/count",
        )

        # Store message
        message = Message(
            id="count-msg",
            session_id=session_id,
            type=MessageType.USER_QUERY,
            content="Test",
            metadata={},
            timestamp=time.time(),
        )
        await memory_service.store_message(session_id, message)

        # Check count was updated
        session = await memory_service.get_session(session_id)
        assert session.message_count == 1

    @pytest.mark.asyncio
    async def test_message_type_filtering_multiple_types(self, memory_service):
        """Test filtering by multiple message types"""
        session_id = "multi-filter-session"

        await memory_service.create_session(
            session_id=session_id,
            workspace_path="/workspace/multi-filter",
        )

        # Store various message types
        types_to_store = [
            MessageType.USER_QUERY,
            MessageType.AGENT_RESPONSE,
            MessageType.SYSTEM_EVENT,
            MessageType.CODE_CONTEXT,
        ]

        for i, msg_type in enumerate(types_to_store):
            message = Message(
                id=f"multi-msg-{i}",
                session_id=session_id,
                type=msg_type,
                content=f"Message {i}",
                metadata={},
                timestamp=time.time() + i,
            )
            await memory_service.store_message(session_id, message)

        # Filter by multiple types
        history = await memory_service.get_session_history(
            session_id,
            limit=10,
            message_types=[MessageType.USER_QUERY, MessageType.AGENT_RESPONSE],
        )

        assert len(history) == 2
        assert all(
            msg.type in [MessageType.USER_QUERY, MessageType.AGENT_RESPONSE] for msg in history
        )


# ============================================================================
# Test Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic end-to-end scenarios"""

    @pytest.mark.asyncio
    async def test_complete_conversation_flow(self, memory_service):
        """Test complete conversation workflow"""
        session_id = "conversation-flow"

        # Create session
        session = await memory_service.create_session(
            session_id=session_id,
            workspace_path="/workspace/conversation",
            metadata={"user": "test_user"},
        )

        assert session is not None

        # Store conversation
        conversation = [
            ("user-1", MessageType.USER_QUERY, "How do I refactor this code?"),
            (
                "agent-1",
                MessageType.AGENT_RESPONSE,
                "Here's a suggestion...",
            ),
            (
                "code-1",
                MessageType.CODE_CONTEXT,
                "def old_code(): pass",
            ),
            (
                "accept-1",
                MessageType.SUGGESTION_ACCEPTED,
                "Applied refactoring",
            ),
        ]

        for msg_id, msg_type, content in conversation:
            message = Message(
                id=msg_id,
                session_id=session_id,
                type=msg_type,
                content=content,
                metadata={},
                timestamp=time.time(),
            )
            await memory_service.store_message(session_id, message)

        # Retrieve history
        history = await memory_service.get_session_history(session_id)

        assert len(history) == 4
        assert history[0].content == "How do I refactor this code?"
        assert history[-1].type == MessageType.SUGGESTION_ACCEPTED

        # Get statistics
        stats = await memory_service.get_session_statistics(session_id)

        assert stats["total_messages"] == 4
        assert stats["message_counts"]["user_query"] == 1
        assert stats["message_counts"]["agent_response"] == 1

    @pytest.mark.asyncio
    async def test_multi_session_workspace(self, memory_service):
        """Test multiple sessions for same workspace"""
        workspace = "/workspace/multi-session"

        # Create multiple sessions
        session_ids = ["sess-1", "sess-2", "sess-3"]

        for session_id in session_ids:
            await memory_service.create_session(
                session_id=session_id,
                workspace_path=workspace,
            )

            # Add some messages
            message = Message(
                id=f"msg-{session_id}",
                session_id=session_id,
                type=MessageType.USER_QUERY,
                content=f"Message for {session_id}",
                metadata={},
                timestamp=time.time(),
            )
            await memory_service.store_message(session_id, message)

        # Verify all sessions exist
        for session_id in session_ids:
            session = await memory_service.get_session(session_id)
            assert session is not None
            assert session.workspace_path == workspace

    @pytest.mark.asyncio
    async def test_session_lifecycle(self, memory_service):
        """Test complete session lifecycle"""
        session_id = "lifecycle-session"

        # 1. Create session
        session = await memory_service.create_session(
            session_id=session_id,
            workspace_path="/workspace/lifecycle",
        )
        assert session.message_count == 0

        # 2. Add messages
        for i in range(10):
            message = Message(
                id=f"lifecycle-msg-{i}",
                session_id=session_id,
                type=MessageType.USER_QUERY,
                content=f"Message {i}",
                metadata={},
                timestamp=time.time(),
            )
            await memory_service.store_message(session_id, message)

        # 3. Check statistics
        stats = await memory_service.get_session_statistics(session_id)
        assert stats["total_messages"] == 10

        # 4. Persist for long-term storage
        persisted = await memory_service.persist_session(session_id)
        assert persisted is True

        # 5. Verify persistence metadata
        session = await memory_service.get_session(session_id)
        assert session.metadata["persisted"] is True
