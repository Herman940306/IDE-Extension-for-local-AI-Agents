"""
Pytest configuration and fixtures for AuraIA System Refactoring v1

Project Creator: Herman Swanepoel
Date: 2025-10-13
"""

import asyncio
from typing import Generator
from unittest.mock import AsyncMock, Mock

import pytest
import redis.asyncio as redis

# ============================================================================
# Pytest Configuration
# ============================================================================


@pytest.fixture(scope="session")
def event_loop() -> Generator:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# ============================================================================
# Redis Fixtures
# ============================================================================


@pytest.fixture
async def mock_redis_client() -> AsyncMock:
    """
    Mock Redis client for testing.

    Provides a fully mocked Redis client with common operations.
    """
    client = AsyncMock(spec=redis.Redis)

    # Mock common Redis operations
    client.get = AsyncMock(return_value=None)
    client.set = AsyncMock(return_value=True)
    client.setex = AsyncMock(return_value=True)
    client.delete = AsyncMock(return_value=1)
    client.exists = AsyncMock(return_value=0)
    client.expire = AsyncMock(return_value=True)
    client.ttl = AsyncMock(return_value=-1)
    client.incr = AsyncMock(return_value=1)
    client.decr = AsyncMock(return_value=0)
    client.hget = AsyncMock(return_value=None)
    client.hset = AsyncMock(return_value=1)
    client.hgetall = AsyncMock(return_value={})
    client.hdel = AsyncMock(return_value=1)
    client.lpush = AsyncMock(return_value=1)
    client.rpush = AsyncMock(return_value=1)
    client.lpop = AsyncMock(return_value=None)
    client.rpop = AsyncMock(return_value=None)
    client.lrange = AsyncMock(return_value=[])
    client.sadd = AsyncMock(return_value=1)
    client.smembers = AsyncMock(return_value=set())
    client.srem = AsyncMock(return_value=1)
    client.ping = AsyncMock(return_value=True)
    client.close = AsyncMock()

    return client


@pytest.fixture
async def redis_connection_pool() -> AsyncMock:
    """
    Mock Redis connection pool for testing.

    Provides a mocked connection pool with get_client method.
    """
    pool = AsyncMock()
    pool.get_client = AsyncMock(return_value=await mock_redis_client())
    pool.close = AsyncMock()
    return pool


# ============================================================================
# LLM Manager Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_response() -> dict:
    """Sample LLM response for testing."""
    return {
        "model": "codellama:7b",
        "created_at": "2025-10-13T10:00:00Z",
        "response": "This is a test response from the LLM.",
        "done": True,
        "context": [],
        "total_duration": 1000000000,
        "load_duration": 100000000,
        "prompt_eval_count": 10,
        "prompt_eval_duration": 200000000,
        "eval_count": 20,
        "eval_duration": 700000000,
    }


@pytest.fixture
async def mock_llm_manager(mock_redis_client: AsyncMock) -> AsyncMock:
    """
    Mock LLM Manager for testing.

    Provides a fully mocked LLM manager with common operations.
    """
    manager = AsyncMock()

    # Mock LLM operations
    manager.generate = AsyncMock(return_value="Generated response")
    manager.generate_with_context = AsyncMock(return_value="Contextual response")
    manager.health_check = AsyncMock(return_value=True)
    manager.get_available_models = AsyncMock(return_value=["codellama:7b", "llama2:7b"])
    manager.load_model = AsyncMock(return_value=True)
    manager.unload_model = AsyncMock(return_value=True)

    # Mock cache
    manager.response_cache = mock_redis_client
    manager.enable_cache = True

    return manager


# ============================================================================
# Response Cache Fixtures
# ============================================================================


@pytest.fixture
async def mock_response_cache(mock_redis_client: AsyncMock) -> AsyncMock:
    """
    Mock Response Cache service for testing.

    Provides a mocked cache service with get/set/delete operations.
    """
    cache = AsyncMock()
    cache.redis_client = mock_redis_client

    # Mock cache operations
    cache.get = AsyncMock(return_value=None)
    cache.set = AsyncMock(return_value=True)
    cache.delete = AsyncMock(return_value=True)
    cache.clear = AsyncMock(return_value=True)
    cache.exists = AsyncMock(return_value=False)
    cache.get_stats = AsyncMock(return_value={"hits": 0, "misses": 0, "hit_rate": 0.0})

    return cache


# ============================================================================
# Rate Limiter Fixtures
# ============================================================================


@pytest.fixture
async def mock_rate_limiter(mock_redis_client: AsyncMock) -> AsyncMock:
    """
    Mock Rate Limiter service for testing.

    Provides a mocked rate limiter with check/reset operations.
    """
    limiter = AsyncMock()
    limiter.redis_client = mock_redis_client

    # Mock rate limiter operations
    limiter.check_rate_limit = AsyncMock(return_value=True)
    limiter.increment = AsyncMock(return_value=1)
    limiter.reset = AsyncMock(return_value=True)
    limiter.get_remaining = AsyncMock(return_value=100)
    limiter.get_reset_time = AsyncMock(return_value=60)

    return limiter


# ============================================================================
# Circuit Breaker Fixtures
# ============================================================================


@pytest.fixture
def mock_circuit_breaker() -> Mock:
    """
    Mock Circuit Breaker for testing.

    Provides a mocked circuit breaker with state management.
    """
    breaker = Mock()

    # Mock circuit breaker state
    breaker.state = "closed"
    breaker.failure_count = 0
    breaker.success_count = 0
    breaker.last_failure_time = None

    # Mock circuit breaker operations
    breaker.call = Mock(side_effect=lambda func, *args, **kwargs: func(*args, **kwargs))
    breaker.record_success = Mock()
    breaker.record_failure = Mock()
    breaker.reset = Mock()
    breaker.is_open = Mock(return_value=False)
    breaker.is_half_open = Mock(return_value=False)
    breaker.is_closed = Mock(return_value=True)

    return breaker


# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def sample_code_context() -> dict:
    """Sample code context for testing."""
    return {
        "file_path": "test.py",
        "language": "python",
        "code": "def hello_world():\n    print('Hello, World!')\n",
        "line_number": 1,
        "column_number": 0,
    }


@pytest.fixture
def sample_task_data() -> dict:
    """Sample task data for testing."""
    return {
        "id": "task-123",
        "type": "code_review",
        "status": "pending",
        "input": {"code": "def test(): pass", "language": "python"},
        "output": None,
        "created_at": "2025-10-13T10:00:00Z",
        "updated_at": "2025-10-13T10:00:00Z",
    }


@pytest.fixture
def sample_agent_config() -> dict:
    """Sample agent configuration for testing."""
    return {
        "name": "test_agent",
        "type": "code_reviewer",
        "capabilities": ["code_review", "bug_detection"],
        "max_retries": 3,
        "timeout": 30,
        "enabled": True,
    }


@pytest.fixture
def sample_llm_prompt() -> str:
    """Sample LLM prompt for testing."""
    return """
    You are a code review assistant. Review the following code:
    
    ```python
    def hello_world():
        print('Hello, World!')
    ```
    
    Provide feedback on:
    1. Code quality
    2. Best practices
    3. Potential improvements
    """


# ============================================================================
# ChromaDB Fixtures
# ============================================================================


@pytest.fixture
def mock_chroma_client() -> Mock:
    """
    Mock ChromaDB client for testing.

    Provides a mocked ChromaDB client with collection operations.
    """
    client = Mock()

    # Mock collection
    collection = Mock()
    collection.add = Mock()
    collection.query = Mock(
        return_value={
            "ids": [["doc1", "doc2"]],
            "distances": [[0.1, 0.2]],
            "documents": [["Document 1", "Document 2"]],
            "metadatas": [[{"source": "test1"}, {"source": "test2"}]],
        }
    )
    collection.get = Mock(
        return_value={
            "ids": ["doc1"],
            "documents": ["Document 1"],
            "metadatas": [{"source": "test1"}],
        }
    )
    collection.delete = Mock()
    collection.count = Mock(return_value=0)

    # Mock client operations
    client.get_collection = Mock(return_value=collection)
    client.create_collection = Mock(return_value=collection)
    client.delete_collection = Mock()
    client.list_collections = Mock(return_value=[])
    client.heartbeat = Mock(return_value=True)

    return client


# ============================================================================
# Test Utilities
# ============================================================================


@pytest.fixture
def assert_async_called_with():
    """
    Utility to assert async mock was called with specific arguments.

    Usage:
        await mock_func("arg1", kwarg="value")
        assert_async_called_with(mock_func, "arg1", kwarg="value")
    """

    def _assert(mock_func: AsyncMock, *args, **kwargs):
        mock_func.assert_called_once_with(*args, **kwargs)

    return _assert


@pytest.fixture
def assert_async_called():
    """
    Utility to assert async mock was called.

    Usage:
        await mock_func()
        assert_async_called(mock_func)
    """

    def _assert(mock_func: AsyncMock):
        mock_func.assert_called_once()

    return _assert


# ============================================================================
# Performance Testing Fixtures
# ============================================================================


@pytest.fixture
def performance_timer():
    """
    Utility to measure execution time.

    Usage:
        with performance_timer() as timer:
            # code to measure
            pass
        assert timer.elapsed < 1.0  # Assert less than 1 second
    """
    import time

    class Timer:
        def __init__(self):
            self.start_time = None
            self.end_time = None
            self.elapsed = None

        def __enter__(self):
            self.start_time = time.time()
            return self

        def __exit__(self, *args):
            self.end_time = time.time()
            self.elapsed = self.end_time - self.start_time

    return Timer


# ============================================================================
# Cleanup
# ============================================================================


@pytest.fixture(autouse=True)
async def cleanup_after_test():
    """Cleanup after each test."""
    yield
    # Add any cleanup logic here
