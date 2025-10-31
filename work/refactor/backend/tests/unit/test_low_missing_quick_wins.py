import sys
from pathlib import Path

# Ensure 'backend' is on sys.path so `src.*` imports resolve when tests
# are run from the workspace root
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import pytest  # noqa: E402
from src.models.session import (
    AgentRunResult,
    TaskSessionResult,
    VerificationStatus,  # noqa: E402
    VerificationSummary,
)
from src.models.task import TaskType  # noqa: E402
from src.services.prompt_templates import PromptTemplates  # noqa: E402
from src.utils.circuit_breaker import CircuitBreaker, CircuitState  # noqa: E402


@pytest.mark.asyncio
async def test_circuit_breaker_state_and_reset():
    cb = CircuitBreaker(name="svc", failure_threshold=1, timeout_seconds=0.01, success_threshold=1)

    # Initial state
    state = cb.get_state()
    assert state["state"] == CircuitState.CLOSED.value
    assert state["failure_count"] == 0

    # Transition to open by invoking a failing call
    async def failing() -> None:
        raise RuntimeError("boom")

    with pytest.raises(RuntimeError):
        await cb.call(failing)

    assert cb.get_state()["state"] in (
        CircuitState.OPEN.value,
        CircuitState.HALF_OPEN.value,
    )

    # Reset should close
    cb.reset()
    assert cb.get_state()["state"] == CircuitState.CLOSED.value


def test_task_session_result_computed_reasoning_field():
    # Build minimal structures
    # Construct valid AgentResponse/Suggestion to satisfy typing
    from src.models.response import AgentResponse, ConfidenceLevel, Suggestion

    suggestion = Suggestion(
        id="s1",
        code="",
        description="",
        confidence=ConfidenceLevel.LOW,
        diff=None,
        applicable_range=None,
    )
    agent_resp = AgentResponse(
        agent_id="a1",
        agent_name="TestAgent",
        suggestions=[suggestion],
        confidence=0.1,
        reasoning="",
        metadata={},
    )
    run = AgentRunResult(
        response=agent_resp,
        duration_ms=1.0,
        escalated=False,
    )
    ver = VerificationSummary(status=VerificationStatus.SKIPPED, confidence=0.0)

    tsr = TaskSessionResult(
        task_id="t1",
        summary="short summary",
        responses=[run],
        verification=ver,
    )
    # computed_field property mirrors summary
    assert tsr.reasoning == "short summary"


def test_prompt_templates_minimal_calls_cover_edges():
    pt = PromptTemplates()
    # Default prompt when task type not in prompts map
    default_prompt = pt.get_system_prompt(TaskType.GENERAL)
    assert "helpful coding assistant" in default_prompt

    ctx = {"language": "python", "file_path": "/tmp/x.py"}
    code = "print('x')"

    assert "Given the following python code" in pt.build_code_suggestion_prompt(code, ctx)
    assert "Analyze this python code" in pt.build_refactor_prompt(code, ctx)
    assert "Generate comprehensive tests for this python code" in pt.build_test_generation_prompt(
        code, ctx
    )
    assert "Analyze this python code for potential bugs" in pt.build_bug_detection_prompt(code, ctx)
    assert (
        "Generate comprehensive documentation for this python code"
        in pt.build_documentation_prompt(code, ctx)
    )
    assert "Perform security analysis on this python code" in pt.build_security_analysis_prompt(
        code, ctx
    )
