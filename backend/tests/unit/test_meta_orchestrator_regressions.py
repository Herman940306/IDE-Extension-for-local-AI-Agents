import types
from typing import Any, Dict, List, Optional
from unittest.mock import AsyncMock, Mock

import pytest
from src.adapters.adapter_utils import AdapterUtils
from src.adapters.base_adapter import AgentAdapter, AgentConfig, Capability
from src.adapters.crewai_adapter import CrewAIAdapter
from src.models import (
    AgentResponse,
    CodeContext,
    ConfidenceLevel,
    Suggestion,
    Task,
    TaskType,
)
from src.orchestrator.meta_orchestrator import MetaOrchestrator
from src.services.embeddings_service import EmbeddingsService
from src.services.llm_manager import LLMError, LLMManager, LLMProvider
from src.services.response_cache import ResponseCache


class _StubAgent(AgentAdapter):
    def __init__(
        self,
        response: Optional[AgentResponse] = None,
        error: Optional[Exception] = None,
        name: str = "Stub Agent",
    ):
        config = AgentConfig(
            name=name,
            description="Test stub agent",
            capabilities=[Capability.DOCUMENTATION],
            metadata={},
        )
        super().__init__(config)
        self._response = response
        self._error = error
        self.calls = 0

    async def initialize(self) -> None:
        self.is_initialized = True

    async def execute_task(
        self, task: Task, context: Optional[CodeContext] = None
    ) -> AgentResponse:
        self.calls += 1
        if self._error:
            raise self._error
        if self._response is None:
            raise AssertionError("Stub agent requires a predefined response")
        return self._response

    async def get_capabilities(self) -> List[Capability]:
        return self.config.capabilities

    async def health_check(self) -> bool:
        return True


def _build_orchestrator() -> MetaOrchestrator:
    llm_manager = Mock(spec=LLMManager)
    context_manager = Mock()
    semantic_search = Mock()
    return MetaOrchestrator(
        llm_manager=llm_manager,
        context_manager=context_manager,
        semantic_search=semantic_search,
    )


class _FlakyRedis:
    def __init__(self, fail_times: int = 2):
        self.fail_times = fail_times
        self.calls = 0
        self.storage: Dict[str, str] = {}

    async def setex(self, key: str, ttl: int, value: str) -> bool:
        self.calls += 1
        if self.calls <= self.fail_times:
            raise ConnectionError("Redis unavailable")
        self.storage[key] = value
        return True

    async def get(self, key: str) -> Optional[str]:
        return self.storage.get(key)

    async def scan_iter(self, match: str):
        prefix = match.rstrip("*")
        for key in list(self.storage.keys()):
            if key.startswith(prefix):
                yield key

    async def delete(self, *keys: str) -> int:
        removed = 0
        for key in keys:
            if key in self.storage:
                del self.storage[key]
                removed += 1
        return removed


class _FlakyCollection:
    def __init__(self):
        self.attempts = 0
        self.records: List[Dict[str, Any]] = []

    def upsert(
        self,
        ids: List[str],
        embeddings: List[List[float]],
        documents: List[str],
        metadatas: List[Dict[str, Any]],
    ) -> None:
        self.attempts += 1
        if self.attempts == 1:
            raise RuntimeError("Chroma write failure")
        self.records.append(
            {
                "ids": list(ids),
                "documents": list(documents),
                "metadatas": list(metadatas),
            }
        )


@pytest.mark.asyncio
async def test_meta_orchestrator_uses_fallback_agent_when_primary_fails():
    orchestrator = _build_orchestrator()

    fallback_response = AgentResponse(
        agent_id="fallback_agent",
        agent_name="Fallback Agent",
        suggestions=[
            Suggestion(
                id="sugg-fallback",
                code="print('fallback')\n",
                description="Return fallback guidance",
                confidence=ConfidenceLevel.MEDIUM,
                diff=None,
                applicable_range=None,
            )
        ],
        confidence=0.6,
        reasoning="Fallback succeeded",
        metadata={"source": "fallback"},
    )

    failing_agent = _StubAgent(
        error=RuntimeError("primary agent failure"), name="Failing Agent"
    )
    fallback_agent = _StubAgent(response=fallback_response, name="Fallback Agent")

    orchestrator.register_agent("primary_agent", failing_agent)
    orchestrator.register_agent("fallback_agent", fallback_agent)

    orchestrator.routing_rules[TaskType.GENERAL] = ["primary_agent", "fallback_agent"]

    task = Task(
        id="task-fallback",
        type=TaskType.GENERAL,
        content="print('hello world')",
        description="Trigger fallback path",
    )

    result = await orchestrator.route_task(task)

    assert result.agent_id == "fallback_agent"
    assert result.metadata["source"] == "fallback"
    assert failing_agent.calls == 1
    assert fallback_agent.calls == 1
    assert orchestrator.agent_health["primary_agent"].consecutive_failures == 1
    assert orchestrator.agent_health["fallback_agent"].success_count == 1


@pytest.mark.asyncio
async def test_meta_orchestrator_aggregates_mixed_responses_without_crashing():
    orchestrator = _build_orchestrator()

    primary_response = AgentResponse(
        agent_id="primary_agent",
        agent_name="Primary Agent",
        suggestions=[
            Suggestion(
                id="sugg-primary",
                code="print('primary')\n",
                description="Primary suggestion",
                confidence=ConfidenceLevel.HIGH,
                diff=None,
                applicable_range=None,
            )
        ],
        confidence=0.9,
        reasoning="Primary agent produced guidance",
        metadata={"source": "primary"},
    )

    primary_agent = _StubAgent(response=primary_response, name="Primary Agent")
    empty_agent_response = AgentResponse(
        agent_id="secondary_agent",
        agent_name="Secondary Agent",
        suggestions=[],
        confidence=0.0,
        reasoning="No actionable guidance",
        metadata={"empty": True},
    )
    empty_agent = _StubAgent(response=empty_agent_response, name="Secondary Agent")

    orchestrator.register_agent("primary_agent", primary_agent)
    orchestrator.register_agent("secondary_agent", empty_agent)

    orchestrator.routing_rules[TaskType.GENERAL] = ["primary_agent", "secondary_agent"]

    task = Task(
        id="task-aggregate",
        type=TaskType.GENERAL,
        content="print('hello world')",
        description="Aggregate mixed responses",
    )

    result = await orchestrator.route_task(task)

    assert result.agent_id == "meta_orchestrator"
    assert len(result.suggestions) == 1
    assert result.suggestions[0].description == "Primary suggestion"
    assert result.confidence == pytest.approx(0.9)
    assert result.metadata["agent_count"] == 2
    assert result.metadata["total_suggestions"] == 1


def test_crewai_adapter_parses_text_without_code_blocks():
    adapter = CrewAIAdapter(
        AgentConfig(
            name="CrewAI Test Agent",
            description="Regression harness",
            capabilities=[Capability.DOCUMENTATION],
            metadata={},
        )
    )

    task = Task(
        id="doc-task",
        type=TaskType.DOCUMENTATION,
        content="def hello():\n    pass\n",
        description="Document the function",
    )

    result_text = "Provide high level documentation summary."  # No code fences present
    response = adapter._convert_crew_result(result_text, task)

    assert response.suggestions
    assert response.suggestions[0].code == result_text
    assert response.suggestions[0].id.startswith("crewai-")
    assert 0.6 <= response.confidence <= 0.9
    assert response.metadata["suggestion_count"] == 1


@pytest.mark.asyncio
async def test_exponential_backoff_recovers_after_transient_failure(monkeypatch):
    attempts = {"count": 0}

    async def flaky():
        attempts["count"] += 1
        if attempts["count"] < 3:
            raise ConnectionError("transient persistence hiccup")
        return "ok"

    async def fast_sleep(_: float):
        return None

    monkeypatch.setattr("src.adapters.adapter_utils.asyncio.sleep", fast_sleep)

    result = await AdapterUtils.exponential_backoff(
        flaky,
        max_retries=3,
        base_delay=0.01,
        max_delay=0.01,
        jitter=False,
    )

    assert result == "ok"
    assert attempts["count"] == 3


@pytest.mark.asyncio
async def test_llm_manager_propagates_rate_limit_error_on_cloud_fallback():
    manager = LLMManager(
        provider=LLMProvider.OLLAMA,
        allow_cloud=True,
        api_key="dummy",
        response_cache=None,
        enable_cache=False,
    )

    manager._generate_ollama = AsyncMock(  # type: ignore[attr-defined]
        side_effect=LLMError("Ollama offline")
    )
    manager._generate_cloud = AsyncMock(  # type: ignore[attr-defined]
        side_effect=LLMError("Cloud provider failure: 429 Too Many Requests")
    )

    with pytest.raises(LLMError) as excinfo:
        await manager.generate(prompt="regular prompt", use_cache=False)

    assert "429" in str(excinfo.value)


@pytest.mark.asyncio
async def test_response_cache_backoff_handles_transient_redis_failure(monkeypatch):
    flaky_redis = _FlakyRedis(fail_times=2)
    cache = ResponseCache(redis_client=flaky_redis, default_ttl=60)
    params = {"scope": "unit"}

    async def cache_set() -> bool:
        success = await cache.set(
            prompt="prompt",
            model="model",
            response={"text": "value"},
            context_params=params,
        )
        if not success:
            raise RuntimeError("Cache set failed")
        return success

    async def fast_sleep(_: float) -> None:
        return None

    monkeypatch.setattr("src.adapters.adapter_utils.asyncio.sleep", fast_sleep)

    result = await AdapterUtils.exponential_backoff(
        cache_set,
        max_retries=3,
        base_delay=0.01,
        jitter=False,
    )

    assert result is True
    cached = await cache.get(prompt="prompt", model="model", context_params=params)
    assert cached is not None
    assert cached["response"]["text"] == "value"
    assert flaky_redis.calls == 3


@pytest.mark.asyncio
async def test_embeddings_service_fallback_writes_after_chroma_batch_failure(tmp_path):
    service = EmbeddingsService()
    service.is_initialized = True
    service.collection = _FlakyCollection()
    embed_counts = {"batch": 0, "single": 0}

    async def fake_embed_code_batch(self, contents: List[str]) -> List[List[float]]:
        embed_counts["batch"] += 1
        return [[float(index + 1)] for index, _ in enumerate(contents)]

    async def fake_embed_code(self, content: str) -> List[float]:
        embed_counts["single"] += 1
        return [0.42]

    service.embed_code_batch = types.MethodType(fake_embed_code_batch, service)
    service.embed_code = types.MethodType(fake_embed_code, service)

    file_one = tmp_path / "one.py"
    file_one.write_text("print('one')\n", encoding="utf-8")
    file_two = tmp_path / "two.py"
    file_two.write_text("print('two')\n", encoding="utf-8")

    await service._process_file_batch([file_one, file_two])

    assert embed_counts["batch"] == 1
    assert embed_counts["single"] == 2
    assert service.collection.attempts == 3
    assert len(service.collection.records) == 2

    stored_ids = {record["ids"][0] for record in service.collection.records}
    expected_ids = {
        service._generate_file_id(str(file_one)),
        service._generate_file_id(str(file_two)),
    }
    assert stored_ids == expected_ids
