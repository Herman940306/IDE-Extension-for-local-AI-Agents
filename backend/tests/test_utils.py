"""
Test utilities for AuraIA System Refactoring v1

Project Creator: Herman Swanepoel
Date: 2025-10-13
"""

import asyncio
import time
from typing import Any, Callable, Dict, List, Optional
from unittest.mock import AsyncMock
import json


# ============================================================================
# Async Testing Utilities
# ============================================================================


async def run_async_test(coro: Callable, *args, **kwargs) -> Any:
    """
    Run an async test function.

    Args:
        coro: Async function to run
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Result of the async function
    """
    return await coro(*args, **kwargs)


def create_async_mock(return_value: Any = None, side_effect: Any = None) -> AsyncMock:
    """
    Create an AsyncMock with optional return value or side effect.

    Args:
        return_value: Value to return when called
        side_effect: Side effect to apply when called

    Returns:
        Configured AsyncMock
    """
    mock = AsyncMock()
    if return_value is not None:
        mock.return_value = return_value
    if side_effect is not None:
        mock.side_effect = side_effect
    return mock


# ============================================================================
# Mock Data Generators
# ============================================================================


def generate_mock_llm_response(
    response_text: str = "Test response", model: str = "codellama:7b", duration_ms: int = 1000
) -> Dict[str, Any]:
    """
    Generate a mock LLM response.

    Args:
        response_text: Response text
        model: Model name
        duration_ms: Duration in milliseconds

    Returns:
        Mock LLM response dictionary
    """
    return {
        "model": model,
        "created_at": "2025-10-13T10:00:00Z",
        "response": response_text,
        "done": True,
        "context": [],
        "total_duration": duration_ms * 1000000,
        "load_duration": duration_ms * 100000,
        "prompt_eval_count": 10,
        "prompt_eval_duration": duration_ms * 200000,
        "eval_count": 20,
        "eval_duration": duration_ms * 700000,
    }


def generate_mock_code_context(
    file_path: str = "test.py", language: str = "python", code: str = "def test(): pass"
) -> Dict[str, Any]:
    """
    Generate a mock code context.

    Args:
        file_path: File path
        language: Programming language
        code: Code content

    Returns:
        Mock code context dictionary
    """
    return {
        "file_path": file_path,
        "language": language,
        "code": code,
        "line_number": 1,
        "column_number": 0,
    }


def generate_mock_task(
    task_id: str = "task-123", task_type: str = "code_review", status: str = "pending"
) -> Dict[str, Any]:
    """
    Generate a mock task.

    Args:
        task_id: Task ID
        task_type: Task type
        status: Task status

    Returns:
        Mock task dictionary
    """
    return {
        "id": task_id,
        "type": task_type,
        "status": status,
        "input": {"code": "def test(): pass", "language": "python"},
        "output": None,
        "created_at": "2025-10-13T10:00:00Z",
        "updated_at": "2025-10-13T10:00:00Z",
    }


# ============================================================================
# Assertion Utilities
# ============================================================================


def assert_dict_contains(actual: Dict, expected: Dict) -> None:
    """
    Assert that actual dictionary contains all keys and values from expected.

    Args:
        actual: Actual dictionary
        expected: Expected dictionary subset

    Raises:
        AssertionError: If expected keys/values not in actual
    """
    for key, value in expected.items():
        assert key in actual, f"Key '{key}' not found in actual dictionary"
        assert actual[key] == value, f"Value mismatch for key '{key}': {actual[key]} != {value}"


def assert_list_contains(actual: List, expected: List) -> None:
    """
    Assert that actual list contains all items from expected.

    Args:
        actual: Actual list
        expected: Expected list subset

    Raises:
        AssertionError: If expected items not in actual
    """
    for item in expected:
        assert item in actual, f"Item '{item}' not found in actual list"


def assert_async_mock_called_with_pattern(mock: AsyncMock, *args_pattern, **kwargs_pattern) -> None:
    """
    Assert that async mock was called with arguments matching pattern.

    Args:
        mock: AsyncMock to check
        *args_pattern: Expected positional arguments pattern
        **kwargs_pattern: Expected keyword arguments pattern

    Raises:
        AssertionError: If mock not called with matching pattern
    """
    assert mock.called, "Mock was not called"

    call_args = mock.call_args
    if args_pattern:
        assert call_args.args == args_pattern, f"Args mismatch: {call_args.args} != {args_pattern}"

    if kwargs_pattern:
        for key, value in kwargs_pattern.items():
            assert key in call_args.kwargs, f"Key '{key}' not in kwargs"
            assert (
                call_args.kwargs[key] == value
            ), f"Value mismatch for '{key}': {call_args.kwargs[key]} != {value}"


# ============================================================================
# Performance Testing Utilities
# ============================================================================


class PerformanceTimer:
    """
    Context manager for measuring execution time.

    Usage:
        with PerformanceTimer() as timer:
            # code to measure
            pass
        print(f"Elapsed: {timer.elapsed_ms}ms")
    """

    def __init__(self):
        self.start_time: Optional[float] = None
        self.end_time: Optional[float] = None
        self.elapsed: Optional[float] = None
        self.elapsed_ms: Optional[float] = None

    def __enter__(self):
        self.start_time = time.time()
        return self

    def __exit__(self, *args):
        self.end_time = time.time()
        self.elapsed = self.end_time - self.start_time
        self.elapsed_ms = self.elapsed * 1000


async def measure_async_performance(coro: Callable, *args, **kwargs) -> tuple[Any, float]:
    """
    Measure performance of an async function.

    Args:
        coro: Async function to measure
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Tuple of (result, elapsed_time_ms)
    """
    start_time = time.time()
    result = await coro(*args, **kwargs)
    elapsed = (time.time() - start_time) * 1000
    return result, elapsed


def assert_performance(elapsed_ms: float, max_ms: float, operation: str = "Operation") -> None:
    """
    Assert that operation completed within time limit.

    Args:
        elapsed_ms: Actual elapsed time in milliseconds
        max_ms: Maximum allowed time in milliseconds
        operation: Operation name for error message

    Raises:
        AssertionError: If elapsed time exceeds maximum
    """
    assert elapsed_ms <= max_ms, f"{operation} took {elapsed_ms:.2f}ms, expected <{max_ms}ms"


# ============================================================================
# Redis Testing Utilities
# ============================================================================


def create_mock_redis_with_data(data: Dict[str, Any]) -> AsyncMock:
    """
    Create a mock Redis client with pre-populated data.

    Args:
        data: Dictionary of key-value pairs

    Returns:
        AsyncMock configured with data
    """
    mock_redis = AsyncMock()

    async def mock_get(key: str) -> Optional[str]:
        return data.get(key)

    async def mock_set(key: str, value: Any, **kwargs) -> bool:
        data[key] = value
        return True

    async def mock_delete(key: str) -> int:
        if key in data:
            del data[key]
            return 1
        return 0

    mock_redis.get = AsyncMock(side_effect=mock_get)
    mock_redis.set = AsyncMock(side_effect=mock_set)
    mock_redis.delete = AsyncMock(side_effect=mock_delete)
    mock_redis.exists = AsyncMock(side_effect=lambda k: 1 if k in data else 0)

    return mock_redis


# ============================================================================
# JSON Testing Utilities
# ============================================================================


def assert_json_equal(actual: str, expected: str) -> None:
    """
    Assert that two JSON strings are equal (ignoring formatting).

    Args:
        actual: Actual JSON string
        expected: Expected JSON string

    Raises:
        AssertionError: If JSON content differs
    """
    actual_obj = json.loads(actual)
    expected_obj = json.loads(expected)
    assert (
        actual_obj == expected_obj
    ), f"JSON mismatch:\nActual: {actual_obj}\nExpected: {expected_obj}"


def assert_json_schema(data: Dict, schema: Dict) -> None:
    """
    Assert that data matches JSON schema structure.

    Args:
        data: Data to validate
        schema: Schema dictionary with expected keys and types

    Raises:
        AssertionError: If data doesn't match schema
    """
    for key, expected_type in schema.items():
        assert key in data, f"Missing key: {key}"
        assert isinstance(
            data[key], expected_type
        ), f"Type mismatch for {key}: {type(data[key])} != {expected_type}"


# ============================================================================
# Exception Testing Utilities
# ============================================================================


async def assert_raises_async(exception_class: type, coro: Callable, *args, **kwargs) -> None:
    """
    Assert that async function raises specific exception.

    Args:
        exception_class: Expected exception class
        coro: Async function to test
        *args: Positional arguments
        **kwargs: Keyword arguments

    Raises:
        AssertionError: If exception not raised or wrong type
    """
    try:
        await coro(*args, **kwargs)
        raise AssertionError(f"Expected {exception_class.__name__} but no exception was raised")
    except exception_class:
        pass  # Expected
    except Exception as e:
        raise AssertionError(f"Expected {exception_class.__name__} but got {type(e).__name__}: {e}")


# ============================================================================
# Retry Testing Utilities
# ============================================================================


async def retry_async(
    coro: Callable, max_retries: int = 3, delay_ms: int = 100, *args, **kwargs
) -> Any:
    """
    Retry an async function with exponential backoff.

    Args:
        coro: Async function to retry
        max_retries: Maximum number of retries
        delay_ms: Initial delay in milliseconds
        *args: Positional arguments
        **kwargs: Keyword arguments

    Returns:
        Result of successful call

    Raises:
        Last exception if all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return await coro(*args, **kwargs)
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                await asyncio.sleep(delay_ms / 1000 * (2**attempt))

    raise last_exception


# ============================================================================
# Logging Testing Utilities
# ============================================================================


class LogCapture:
    """
    Capture log messages for testing.

    Usage:
        with LogCapture() as logs:
            logger.info("test message")
        assert "test message" in logs.messages
    """

    def __init__(self):
        self.messages: List[str] = []
        self.records: List[Dict] = []

    def __enter__(self):
        return self

    def __exit__(self, *args):
        pass

    def capture(self, message: str, **kwargs):
        """Capture a log message."""
        self.messages.append(message)
        self.records.append({"message": message, **kwargs})

    def assert_logged(self, message: str) -> None:
        """Assert that message was logged."""
        assert message in self.messages, f"Message '{message}' not found in logs: {self.messages}"

    def assert_not_logged(self, message: str) -> None:
        """Assert that message was not logged."""
        assert message not in self.messages, f"Message '{message}' found in logs but shouldn't be"


# ============================================================================
# Test Data Builders
# ============================================================================


class TestDataBuilder:
    """
    Builder pattern for creating test data.
    
    Usage:
        task = TestDataBuilder.task()\\
            .with_id("task-123")\\
            .with_type("code_review")\\
            .with_status("completed")\\
            .build()
    """

    @staticmethod
    def task():
        """Start building a task."""
        return TaskBuilder()

    @staticmethod
    def code_context():
        """Start building a code context."""
        return CodeContextBuilder()

    @staticmethod
    def llm_response():
        """Start building an LLM response."""
        return LLMResponseBuilder()


class TaskBuilder:
    """Builder for task test data."""

    def __init__(self):
        self.data = generate_mock_task()

    def with_id(self, task_id: str):
        self.data["id"] = task_id
        return self

    def with_type(self, task_type: str):
        self.data["type"] = task_type
        return self

    def with_status(self, status: str):
        self.data["status"] = status
        return self

    def with_input(self, input_data: Dict):
        self.data["input"] = input_data
        return self

    def with_output(self, output_data: Dict):
        self.data["output"] = output_data
        return self

    def build(self) -> Dict:
        return self.data


class CodeContextBuilder:
    """Builder for code context test data."""

    def __init__(self):
        self.data = generate_mock_code_context()

    def with_file_path(self, file_path: str):
        self.data["file_path"] = file_path
        return self

    def with_language(self, language: str):
        self.data["language"] = language
        return self

    def with_code(self, code: str):
        self.data["code"] = code
        return self

    def build(self) -> Dict:
        return self.data


class LLMResponseBuilder:
    """Builder for LLM response test data."""

    def __init__(self):
        self.data = generate_mock_llm_response()

    def with_response(self, response: str):
        self.data["response"] = response
        return self

    def with_model(self, model: str):
        self.data["model"] = model
        return self

    def with_duration(self, duration_ms: int):
        self.data["total_duration"] = duration_ms * 1000000
        return self

    def build(self) -> Dict:
        return self.data
