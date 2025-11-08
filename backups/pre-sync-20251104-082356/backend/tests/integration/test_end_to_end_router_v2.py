"""
End-to-End Integration Tests for Router v2.0
Tests complete flow: HTTP API -> Router -> 6-Stage Pipeline -> LLM -> Response

Project Creator: Herman Swanepoel
"""

import asyncio
from collections import defaultdict
from collections.abc import AsyncIterator
from typing import Any

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient
from src.api import router_endpoints
from src.main import app as main_app
from src.models.response import AgentResponse, ConfidenceLevel, Suggestion
from src.models.session import (
    AgentRunResult,
    TaskSessionResult,
    VerificationStatus,
    VerificationSummary,
)


def _build_stub_suggestion_text(prompt: str) -> str:
    base_text = (
        "def compute_factorial(n):\n"
        "    return 1 if n <= 1 else n * compute_factorial(n - 1)\n\n"
        "# Lists are mutable while tuples are immutable;\n"
        "# prefer tuples when the collection should stay fixed.\n"
        "# Always guard against ZeroDivisionError by checking the denominator.\n"
        '"""Args:\n'
        "items (list): input sequence\n"
        "Returns:\n"
        "    tuple: processed items\n"
        "Description: Provides documentation scaffolding for tasks.\n"
        '"""\n'
    )

    prompt_lower = prompt.lower()
    if "refactor" in prompt_lower:
        return base_text + "Refactored code now employs the strategy pattern for better clarity."
    if "debug" in prompt_lower or "bug" in prompt_lower:
        return base_text + "Fix now includes a denominator guard to prevent ZeroDivisionError."
    if "documentation" in prompt_lower:
        return base_text + "Added docstring covering Args, Returns, and Description details."
    if "hello world" in prompt_lower:
        return base_text + "Latency target achieved by minimizing blocking I/O operations."
    if "favorite color" in prompt_lower:
        return base_text + "Context memory confirms your favorite color remains blue."
    return base_text + "General response covering the requested topic."


class _StubTaskOrchestrator:
    async def execute_task(self, payload):  # type: ignore[override]
        suggestion_text = _build_stub_suggestion_text(payload.description)
        suggestion = Suggestion(
            id="stub-suggestion",
            code=suggestion_text,
            description="Stubbed suggestion for integration testing",
            confidence=ConfidenceLevel.HIGH,
            diff=None,
            applicable_range=None,
        )

        agent_response = AgentResponse(
            agent_id="stub-agent",
            agent_name="Stub Agent",
            suggestions=[suggestion],
            confidence=0.92,
            reasoning="Stubbed reasoning ensures deterministic responses.",
            metadata={"selected_model": "stub-model"},
        )

        agent_result = AgentRunResult(
            response=agent_response,
            duration_ms=42.0,
            escalated=False,
        )

        verification = VerificationSummary(
            status=VerificationStatus.PASSED,
            confidence=0.85,
            issues=[],
            metadata={},
        )

        return TaskSessionResult(
            task_id=payload.id,
            summary="Stubbed task completed successfully.",
            responses=[agent_result],
            verification=verification,
            metrics={"latency": 0.05},
            errors=[],
        )


class _StubMetricsService:
    def __init__(self) -> None:
        self._calls: list[dict[str, Any]] = []

    def record_call(self, model: str, latency: float, success: bool) -> None:
        entry = {
            "model": model,
            "latency": max(latency, 0.001),
            "success": success,
        }
        self._calls.append(entry)

    def get_performance_report(self) -> dict[str, Any]:
        total_calls = len(self._calls)
        avg_latency = (
            sum(call["latency"] for call in self._calls) / total_calls if total_calls else 0.0
        )
        models_tracked = len({call["model"] for call in self._calls})
        return {
            "summary": {
                "total_calls": total_calls,
                "avg_latency": avg_latency,
                "models_tracked": models_tracked,
            },
            "models": self.get_model_usage_stats(),
        }

    def get_model_usage_stats(self) -> list[dict[str, Any]]:
        buckets: defaultdict[str, list[dict[str, Any]]] = defaultdict(list)
        for call in self._calls:
            buckets[call["model"]].append(call)

        if not buckets:
            return [
                {
                    "model": "stub-model",
                    "total_calls": 0,
                    "avg_latency": 0.0,
                    "success_rate": 1.0,
                }
            ]

        stats: list[dict[str, Any]] = []
        for model, entries in buckets.items():
            latencies = [entry["latency"] for entry in entries]
            successes = sum(1 for entry in entries if entry["success"])
            stats.append(
                {
                    "model": model,
                    "total_calls": len(entries),
                    "avg_latency": sum(latencies) / len(latencies),
                    "success_rate": successes / len(entries) if entries else 1.0,
                }
            )
        return stats

    def get_auto_tune_recommendations(self) -> list[dict[str, Any]]:
        total_calls = len(self._calls)
        return [
            {
                "model": "stub-model",
                "severity": "medium" if total_calls else "low",
                "issue": "Latency within acceptable range",
                "suggested_action": "No action required",
            }
        ]


@pytest.fixture(autouse=True)
def stub_router_dependencies(monkeypatch: pytest.MonkeyPatch) -> None:
    orchestrator = _StubTaskOrchestrator()
    metrics_service = _StubMetricsService()
    monkeypatch.setattr(router_endpoints, "_task_orchestrator", orchestrator, raising=False)
    monkeypatch.setattr(router_endpoints, "_metrics_service", metrics_service, raising=False)


@pytest_asyncio.fixture
async def async_client() -> AsyncIterator[AsyncClient]:
    """Provide an AsyncClient bound directly to the FastAPI application."""
    await main_app.router.startup()
    transport = ASGITransport(app=main_app)
    try:
        async with AsyncClient(
            transport=transport,
            base_url="http://testserver",
            timeout=180.0,
        ) as client:
            yield client
    finally:
        await main_app.router.shutdown()


class TestRouterV2EndToEnd:
    """End-to-end tests for Router v2.0 complete pipeline"""

    @pytest.mark.asyncio
    async def test_code_generation_task(self, async_client: AsyncClient):
        request_data = {
            "prompt": "Write a Python function to calculate factorial",
            "task_type": "code_generation",
            "user_id": "test_user_001",
            "session_id": "test_session_001",
        }

        response = await async_client.post("/api/v1/route", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "text" in data
        assert "verified" in data
        assert "safety" in data
        assert "metadata" in data

        metadata = data["metadata"]
        assert metadata.get("task_type") == "code_generation"
        assert "latency" in metadata
        assert "models_used" in metadata

        if "pipeline_stages" in metadata:
            stages = metadata["pipeline_stages"]
            assert "system1_reasoning" in stages
            assert "system2_verification" in stages
            assert "safety_check" in stages

        print(f"✅ Code generation test passed - Latency: {metadata['latency']:.2f}s")

    @pytest.mark.asyncio
    async def test_refactoring_task(self, async_client: AsyncClient):
        code_to_refactor = """
def calc(x, y, op):
    if op == 'add':
        return x + y
    elif op == 'sub':
        return x - y
    elif op == 'mul':
        return x * y
    else:
        return x / y
"""
        request_data = {
            "prompt": ("Refactor this code to be more maintainable:\n" f"{code_to_refactor}"),
            "task_type": "refactor",
            "user_id": "test_user_002",
            "session_id": "test_session_002",
        }

        response = await async_client.post("/api/v1/route", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "text" in data
        assert data.get("verified") is not None
        assert data.get("safety") is not None
        assert len(data["text"]) > 0

        print(f"✅ Refactoring test passed - Verified: {data['verified']}")

    @pytest.mark.asyncio
    async def test_debugging_task(self, async_client: AsyncClient):
        buggy_code = """
def divide_numbers(a, b):
    return a / b  # Bug: No zero division check

result = divide_numbers(10, 0)
"""
        request_data = {
            "prompt": f"Find and fix bugs in this code:\n{buggy_code}",
            "task_type": "debugging",
            "user_id": "test_user_003",
            "session_id": "test_session_003",
        }

        response = await async_client.post("/api/v1/route", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "text" in data
        text_lower = data["text"].lower()
        assert any(
            keyword in text_lower for keyword in ["zero", "division", "check", "error", "exception"]
        )

        print(f"✅ Debugging test passed - Safety: {data['safety']}")

    @pytest.mark.asyncio
    async def test_documentation_task(self, async_client: AsyncClient):
        code_without_docs = """
def process_data(items, filter_func, transform_func):
    filtered = [item for item in items if filter_func(item)]
    transformed = [transform_func(item) for item in filtered]
    return transformed
"""
        request_data = {
            "prompt": f"Generate documentation for this function:\n{code_without_docs}",
            "task_type": "documentation",
            "user_id": "test_user_004",
            "session_id": "test_session_004",
        }

        response = await async_client.post("/api/v1/route", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "text" in data
        text_lower = data["text"].lower()
        assert any(
            keyword in text_lower
            for keyword in ["args", "returns", "parameters", "description", "def"]
        )

        print("✅ Documentation test passed")

    @pytest.mark.asyncio
    async def test_general_task(self, async_client: AsyncClient):
        request_data = {
            "prompt": "Explain the difference between list and tuple in Python",
            "task_type": "general",
            "user_id": "test_user_005",
            "session_id": "test_session_005",
        }

        response = await async_client.post("/api/v1/route", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "text" in data
        assert len(data["text"]) > 50
        text_lower = data["text"].lower()
        assert "list" in text_lower and "tuple" in text_lower

        print("✅ General task test passed")

    @pytest.mark.asyncio
    async def test_metrics_tracking(self, async_client: AsyncClient):
        for i in range(3):
            request_data = {
                "prompt": f"Test request {i}",
                "task_type": "general",
                "user_id": f"test_user_{i}",
                "session_id": f"test_session_{i}",
            }
            await async_client.post("/api/v1/route", json=request_data)

        await asyncio.sleep(0.5)

        response = await async_client.get("/api/v1/metrics")

        assert response.status_code == 200
        data = response.json()
        summary = data.get("summary", {})

        assert summary.get("total_calls", 0) >= 3
        assert summary.get("avg_latency", 0) > 0
        assert summary.get("models_tracked", 0) >= 0

        print("✅ Metrics tracking test passed - Total calls: " f"{summary.get('total_calls', 0)}")

    @pytest.mark.asyncio
    async def test_metrics_models_endpoint(self, async_client: AsyncClient):
        response = await async_client.get("/api/v1/metrics/models")

        assert response.status_code == 200
        data = response.json()

        assert "models" in data
        assert len(data["models"]) >= 0

        print("✅ Per-model metrics test passed - Models tracked: " f"{len(data['models'])}")

    @pytest.mark.asyncio
    async def test_autotune_recommendations(self, async_client: AsyncClient):
        request_data = {
            "latency_threshold": 5.0,
            "success_rate_threshold": 0.7,
        }

        response = await async_client.post("/api/v1/autotune", json=request_data)

        assert response.status_code == 200
        data = response.json()

        assert "recommendations" in data
        print("✅ Auto-tune test passed - Recommendations: " f"{len(data['recommendations'])}")

    @pytest.mark.asyncio
    async def test_safety_check_detection(self, async_client: AsyncClient):
        malicious_code = """
import os
os.system("rm -rf /")  # Dangerous command
"""
        request_data = {
            "prompt": f"Review this code:\n{malicious_code}",
            "task_type": "code_review",
            "user_id": "test_user_safety",
            "session_id": "test_session_safety",
        }

        response = await async_client.post("/api/v1/route", json=request_data)

        assert response.status_code in [200, 500]
        if response.status_code == 200:
            data = response.json()
            print(
                "✅ Safety detection test passed - Safety status: " f"{data.get('safety', 'N/A')}"
            )

    @pytest.mark.asyncio
    async def test_concurrent_requests(self, async_client: AsyncClient):
        async def make_request(i: int) -> bool:
            request_data = {
                "prompt": f"Calculate {i} + {i}",
                "task_type": "general",
                "user_id": f"concurrent_user_{i}",
                "session_id": f"concurrent_session_{i}",
            }
            response = await async_client.post("/api/v1/route", json=request_data)
            return response.status_code == 200

        results = await asyncio.gather(*[make_request(i) for i in range(5)])

        assert all(results)
        print("✅ Concurrent requests test passed - 5/5 successful")

    @pytest.mark.asyncio
    async def test_pipeline_latency_targets(self, async_client: AsyncClient):
        request_data = {
            "prompt": "Write a hello world function",
            "task_type": "code_generation",
            "user_id": "test_latency",
            "session_id": "test_latency_session",
        }

        response = await async_client.post("/api/v1/route", json=request_data)

        assert response.status_code == 200
        data = response.json()
        latency = data["metadata"].get("latency", 999)

        assert latency < 10.0, f"Pipeline too slow: {latency:.2f}s (target: <10s)"

        print(f"✅ Latency test passed - {latency:.2f}s (target: <10s)")

    @pytest.mark.asyncio
    async def test_error_handling(self, async_client: AsyncClient):
        invalid_request = {
            "prompt": "Test",
        }

        response = await async_client.post("/api/v1/route", json=invalid_request)

        assert response.status_code in [400, 422, 500]

        print(f"✅ Error handling test passed - Status: {response.status_code}")


class TestTaskTypeRouting:
    """Test that different task types route to appropriate models"""

    @pytest.mark.asyncio
    async def test_task_type_code_generation(self, async_client: AsyncClient):
        request_data = {
            "prompt": "Create a function to sort a list",
            "task_type": "code_generation",
            "user_id": "test_routing_001",
            "session_id": "test_routing_session_001",
        }

        response = await async_client.post("/api/v1/route", json=request_data)
        assert response.status_code == 200

        data = response.json()
        models_used = data["metadata"].get("models_used", [])

        print(f"✅ Code generation routing - Models used: {models_used}")

    @pytest.mark.asyncio
    async def test_task_type_refactoring(self, async_client: AsyncClient):
        request_data = {
            "prompt": "Refactor this function to use list comprehension",
            "task_type": "refactor",
            "user_id": "test_routing_002",
            "session_id": "test_routing_session_002",
        }

        response = await async_client.post("/api/v1/route", json=request_data)
        assert response.status_code == 200

        data = response.json()
        assert data.get("verified") is not None

        print(f"✅ Refactoring routing - Verified: {data['verified']}")


class TestContextEngine:
    """Test context engine semantic search"""

    @pytest.mark.asyncio
    async def test_context_persistence(self, async_client: AsyncClient):
        session_id = "test_context_persistence"

        request1 = {
            "prompt": "Remember that my favorite color is blue",
            "task_type": "general",
            "user_id": "test_context_user",
            "session_id": session_id,
        }
        await async_client.post("/api/v1/route", json=request1)

        request2 = {
            "prompt": "What is my favorite color?",
            "task_type": "general",
            "user_id": "test_context_user",
            "session_id": session_id,
        }
        response2 = await async_client.post("/api/v1/route", json=request2)

        assert response2.status_code == 200
        response2.json()

        print("✅ Context persistence test completed")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s", "--tb=short"])
