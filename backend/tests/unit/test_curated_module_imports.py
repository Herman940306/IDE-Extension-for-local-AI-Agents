from src.config.settings import get_settings
from src.models.response import AgentResponse, ConfidenceLevel, Suggestion
from src.models.session import (
    AgentRunResult,
    TaskRequestPayload,
    TaskSessionResult,
    VerificationStatus,
    VerificationSummary,
)
from src.models.task import TaskType
from src.orchestrator.task_router import TaskRouter


def test_models_and_settings_basic_usage():
    # Exercise models.response
    sugg = Suggestion(
        id="s1",
        code="def f():\n    return 1",
        description="demo",
        confidence=ConfidenceLevel.HIGH,
    )
    resp = AgentResponse(
        agent_id="a1",
        agent_name="Agent",
        suggestions=[sugg],
        confidence=0.9,
        reasoning="ok",
    )

    # Exercise models.session
    req = TaskRequestPayload(
        id="t1",
        type=TaskType.GENERAL,
        description="demo",
        content=None,
    )
    run = AgentRunResult(response=resp, duration_ms=1.0, escalated=False)
    ver = VerificationSummary(status=VerificationStatus.PASSED, confidence=0.9)
    sess = TaskSessionResult(
        task_id=req.id,
        status="completed",
        summary="done",
        responses=[run],
        verification=ver,
        metrics={"duration_ms": 1.0},
    )
    assert sess.reasoning == "done"

    # Exercise config.settings
    settings = get_settings()
    # Basic sanity on expected fields present in our Settings
    assert hasattr(settings, "reasoner_model")
    assert hasattr(settings, "conversational_model")


def test_task_router_intents():
    router = TaskRouter()
    assert router.detect_intent("please refactor this function") == router.detect_intent("refactor")
    # Allow either 'generate' or 'test' intents for wording variants
    intent = router.detect_intent("write unit tests")
    assert intent.value in {"generate", "test"}
