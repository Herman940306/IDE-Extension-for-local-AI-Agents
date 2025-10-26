"""
Unit tests for CrewAI adapter
Project Creator: Herman Swanepoel
"""

from __future__ import annotations

import asyncio
from types import SimpleNamespace
from typing import Any, Callable, List
from unittest.mock import patch

import pytest

from src.adapters.base_adapter import AgentConfig, Capability
from src.adapters.crewai_adapter import CrewAIAdapter, CrewAIDependencies
from src.models import (
    CodeContext,
    Priority,
    Task,
    TaskType,
)


class DummyAgent:
    """Lightweight stand-in for CrewAI Agent objects."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs
        self.role = kwargs.get("role", "Dummy Agent")


class DummyTask:
    """Minimal CrewAI Task replacement used in tests."""

    def __init__(
        self,
        name: str,
        description: str,
        expected_output: str,
        agent: Any,
        markdown: bool = True,
    ) -> None:
        self.name = name
        self.description = description
        self.expected_output = expected_output
        self.agent = agent
        self.markdown = markdown


class DummyResult:
    """Container to simulate CrewAI execution results."""

    def __init__(
        self,
        raw: str,
        tasks_output: List[Any],
        token_usage: Any = None,
    ) -> None:
        self.raw = raw
        self.tasks_output = tasks_output
        self.token_usage = token_usage


class DummyAsyncCrew:
    """Crew stub exposing an async kickoff entry point."""

    def __init__(self, *, agents: list[Any], tasks: list[Any], process: Any, verbose: bool) -> None:
        self.agents = agents
        self.tasks = tasks
        self.process = process
        self.verbose = verbose
        self.kickoff_async_called = False
        self.inputs: dict[str, Any] | None = None
        global ASYNC_CREW_LAST_INSTANCE
        ASYNC_CREW_LAST_INSTANCE = self

    async def kickoff_async(self, *, inputs: dict[str, Any]) -> DummyResult:
        self.kickoff_async_called = True
        self.inputs = inputs
        factory = ASYNC_CREW_RESULT_FACTORY or _empty_result
        return factory()


class DummySyncCrew:
    """Crew stub exposing only a synchronous kickoff."""

    def __init__(self, *, agents: list[Any], tasks: list[Any], process: Any, verbose: bool) -> None:
        self.agents = agents
        self.tasks = tasks
        self.process = process
        self.verbose = verbose
        self.kickoff_called = False
        self.inputs: dict[str, Any] | None = None
        global SYNC_CREW_LAST_INSTANCE
        SYNC_CREW_LAST_INSTANCE = self

    def kickoff(self, *, inputs: dict[str, Any]) -> DummyResult:
        self.kickoff_called = True
        self.inputs = inputs
        factory = SYNC_CREW_RESULT_FACTORY or _empty_result
        return factory()


def _empty_result() -> DummyResult:
    """Provide an empty result placeholder for fallback code paths."""

    return DummyResult(raw="", tasks_output=[])


ASYNC_CREW_RESULT_FACTORY: Callable[[], DummyResult] | None = None
ASYNC_CREW_LAST_INSTANCE: DummyAsyncCrew | None = None
SYNC_CREW_RESULT_FACTORY: Callable[[], DummyResult] | None = None
SYNC_CREW_LAST_INSTANCE: DummySyncCrew | None = None


class DummyLLM:
    """Simple callable object that mimics the LangChain Ollama client."""

    def __init__(self, **kwargs: Any) -> None:
        self.kwargs = kwargs

    def __call__(self, prompt: str) -> str:
        return "pong" if prompt == "ping" else ""


@pytest.fixture
def adapter_config() -> AgentConfig:
    """Provide a reusable CrewAI adapter configuration."""

    return AgentConfig(
        name="CrewAI Test Agent",
        description="Adapter used for unit testing",
        capabilities=[Capability.DOCUMENTATION, Capability.TESTING],
        enabled=True,
        max_concurrent=1,
        timeout=30,
        metadata={"model": "codellama:7b", "verbose": False},
    )


@pytest.fixture
def documentation_task() -> Task:
    """Create a documentation task consumed by the adapter."""

    return Task(
        id="task-doc-1",
        type=TaskType.DOCUMENTATION,
        content="Document the provided module",
        priority=Priority.MEDIUM,
        description="Write documentation for the module",
        metadata={"prompt": "Provide API overview"},
    )


@pytest.fixture
def code_context() -> CodeContext:
    """Provide representative code context for tasks."""

    return CodeContext(
        file_path="src/example.py",
        language="python",
        code="def sample():\n    return True",
        selected_text=None,
        workspace_path="/workspace",
        cursor_position={"line": 0, "character": 0},
        surrounding_code="",
        imports=[],
        dependencies=[],
        git_branch="main",
    )


def _build_dependencies(crew_cls: type[Any]) -> CrewAIDependencies:
    """Helper to create CrewAIDependencies with the supplied crew class."""

    process = SimpleNamespace(sequential="sequential")
    return CrewAIDependencies(
        agent_cls=DummyAgent,
        crew_cls=crew_cls,
        process_enum=process,
        task_cls=DummyTask,
    )


@pytest.mark.asyncio
async def test_initialize_configures_agents(adapter_config: AgentConfig) -> None:
    """Adapter initialization should construct CrewAI agents and cache dependencies."""

    adapter = CrewAIAdapter(adapter_config)
    dependencies = _build_dependencies(DummyAsyncCrew)

    with patch.object(
        CrewAIAdapter,
        "_load_crewai_dependencies",
        return_value=dependencies,
    ), patch.object(
        CrewAIAdapter,
        "_load_ollama_client",
        return_value=DummyLLM,
    ):
        await adapter.initialize()

    assert adapter.is_initialized is True
    assert isinstance(adapter.llm, DummyLLM)
    assert adapter.doc_agent is not None
    assert adapter.test_agent is not None


@pytest.mark.asyncio
async def test_execute_task_uses_async_kickoff(
    adapter_config: AgentConfig,
    documentation_task: Task,
    code_context: CodeContext,
) -> None:
    """Executing a task should invoke the async kickoff path when available."""

    adapter = CrewAIAdapter(adapter_config)
    dependencies = _build_dependencies(DummyAsyncCrew)

    tasks_output = [
        SimpleNamespace(
            raw="""```python\nprint('hello')\n```""",
            summary="Documented behavior",
            description="Generated documentation",
            agent="Documentation Specialist",
        )
    ]
    global ASYNC_CREW_RESULT_FACTORY, ASYNC_CREW_LAST_INSTANCE
    ASYNC_CREW_RESULT_FACTORY = lambda: DummyResult(
        raw="""```python\nprint('hello')\n```""",
        tasks_output=tasks_output,
        token_usage=SimpleNamespace(model_dump=lambda: {"total_tokens": 42}),
    )
    ASYNC_CREW_LAST_INSTANCE = None

    try:
        with patch.object(
            CrewAIAdapter,
            "_load_crewai_dependencies",
            return_value=dependencies,
        ), patch.object(
            CrewAIAdapter,
            "_load_ollama_client",
            return_value=DummyLLM,
        ):
            await adapter.initialize()
            response = await adapter.execute_task(documentation_task, code_context)
    finally:
        ASYNC_CREW_RESULT_FACTORY = None
        ASYNC_CREW_LAST_INSTANCE = None

    assert response.suggestions, "Expected at least one suggestion from CrewAI output"
    assert response.metadata["crew_agents"] == ["Documentation Specialist"]

    crew_instance = ASYNC_CREW_LAST_INSTANCE
    assert crew_instance is not None
    assert crew_instance.kickoff_async_called is True
    assert crew_instance.inputs == {
        "file_path": code_context.file_path,
        "language": code_context.language,
        "task_id": documentation_task.id,
    }
    assert response.metadata["token_usage"] == {"total_tokens": 42}


@pytest.mark.asyncio
async def test_execute_task_falls_back_to_sync_kickoff(
    adapter_config: AgentConfig,
    documentation_task: Task,
    code_context: CodeContext,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """If async kickoff is unavailable the adapter should run the sync variant in a thread."""

    adapter = CrewAIAdapter(adapter_config)
    dependencies = _build_dependencies(DummySyncCrew)

    global SYNC_CREW_RESULT_FACTORY, SYNC_CREW_LAST_INSTANCE
    SYNC_CREW_RESULT_FACTORY = lambda: DummyResult(
        raw="""```python\nprint('sync')\n```""",
        tasks_output=[],
    )
    SYNC_CREW_LAST_INSTANCE = None

    async def immediate_to_thread(func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        return func(*args, **kwargs)

    monkeypatch.setattr(asyncio, "to_thread", immediate_to_thread)

    try:
        with patch.object(
            CrewAIAdapter,
            "_load_crewai_dependencies",
            return_value=dependencies,
        ), patch.object(
            CrewAIAdapter,
            "_load_ollama_client",
            return_value=DummyLLM,
        ):
            await adapter.initialize()
            response = await adapter.execute_task(documentation_task, code_context)
    finally:
        SYNC_CREW_RESULT_FACTORY = None
        SYNC_CREW_LAST_INSTANCE = None

    assert response.suggestions, "Sync kickoff should still yield suggestions"

    crew_instance = SYNC_CREW_LAST_INSTANCE
    assert crew_instance is not None
    assert crew_instance.kickoff_called is True
    assert crew_instance.inputs == {
        "file_path": code_context.file_path,
        "language": code_context.language,
        "task_id": documentation_task.id,
    }


@pytest.mark.asyncio
async def test_execute_task_returns_placeholder_when_capability_missing(
    adapter_config: AgentConfig,
    code_context: CodeContext,
) -> None:
    """Tasks without matching capabilities should short-circuit with a low-confidence response."""

    adapter = CrewAIAdapter(adapter_config)
    dependencies = _build_dependencies(DummyAsyncCrew)

    unrelated_task = Task(
        id="task-bug-1",
        type=TaskType.BUG_DETECTION,
        content="Identify potential bugs",
        priority=Priority.MEDIUM,
        description="Analyse code for bugs",
    )

    with patch.object(
        CrewAIAdapter,
        "_load_crewai_dependencies",
        return_value=dependencies,
    ), patch.object(
        CrewAIAdapter,
        "_load_ollama_client",
        return_value=DummyLLM,
    ):
        await adapter.initialize()
        response = await adapter.execute_task(unrelated_task, code_context)

    assert response.suggestions == []
    assert response.confidence == 0.35
    assert "CrewAI adapter does not provide an agent" in response.reasoning
```
