"""
Unit tests for Reasoning Coordinator
Project Creator: Herman Swanepoel
"""

import asyncio
from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.models.reasoner import FastReasoner, ReasoningResponse
from src.models.verifier import AnalyticalVerifier, VerificationResponse
from src.orchestrator.meta_controller import MetaController
from src.orchestrator.reasoning_coordinator import (
    ProcessingMode,
    ReasoningCoordinator,
    ReasoningResult,
)
from src.orchestrator.task_router import TaskRouter


@pytest.fixture
def mock_reasoner():
    """Mock FastReasoner"""
    reasoner = Mock(spec=FastReasoner)
    reasoner.reason = AsyncMock(
        return_value=ReasoningResponse(
            suggestions=["def improved_function():\n    pass"],
            confidence=0.85,
            reasoning="Fast heuristic reasoning",
            latency_ms=150.0,
            model="llama3.2:3b",
        )
    )
    reasoner.get_stats = Mock(
        return_value={"model": "llama3.2:3b", "total_requests": 10, "avg_latency_ms": 150.0}
    )
    reasoner.close = AsyncMock()
    return reasoner


@pytest.fixture
def mock_verifier():
    """Mock AnalyticalVerifier"""
    verifier = Mock(spec=AnalyticalVerifier)
    verifier.verify = AsyncMock(
        return_value=VerificationResponse(
            valid=True,
            confidence=0.92,
            issues=[],
            suggestions=["Consider adding type hints"],
            reasoning="Analytical verification passed",
            latency_ms=800.0,
            model="mistral:7b",
        )
    )
    verifier.get_stats = Mock(
        return_value={"model": "mistral:7b", "total_verifications": 5, "avg_latency_ms": 800.0}
    )
    verifier.close = AsyncMock()
    return verifier


@pytest.fixture
def task_router():
    """Real TaskRouter instance"""
    return TaskRouter()


@pytest.fixture
def meta_controller():
    """Real MetaController instance"""
    return MetaController()


@pytest.fixture
def coordinator(mock_reasoner, mock_verifier, task_router, meta_controller):
    """ReasoningCoordinator with mocked dependencies"""
    return ReasoningCoordinator(
        reasoner=mock_reasoner,
        verifier=mock_verifier,
        task_router=task_router,
        meta_controller=meta_controller,
        confidence_threshold=0.75,
        complexity_threshold=0.5,
    )


@pytest.mark.asyncio
async def test_system1_only_simple_task(coordinator, mock_reasoner):
    """Test System 1 only path for simple tasks"""
    result = await coordinator.process(
        task_type="explain",
        description="Explain this function",
        code_context="def hello(): print('hi')",
        language="python",
        mode=ProcessingMode.SYSTEM1_ONLY,
    )

    assert result["success"] is True
    assert len(result["suggestions"]) > 0
    assert result["verification_skipped"] is True
    assert result["system2_response"] is None
    mock_reasoner.reason.assert_called_once()


@pytest.mark.asyncio
async def test_dual_process_complex_task(coordinator, mock_reasoner, mock_verifier):
    """Test dual-process path for complex tasks"""
    result = await coordinator.process(
        task_type="refactor",
        description="Refactor this complex function",
        code_context="def complex_func():\n" + "    pass\n" * 50,
        language="python",
        mode=ProcessingMode.DUAL_PROCESS,
    )

    assert result["success"] is True
    assert result["system1_response"] is not None
    assert result["system2_response"] is not None
    assert result["verification_passed"] is True
    mock_reasoner.reason.assert_called_once()
    mock_verifier.verify.assert_called_once()


@pytest.mark.asyncio
async def test_adaptive_mode_low_confidence_escalation(coordinator, mock_reasoner, mock_verifier):
    """Test adaptive mode escalates on low confidence"""
    # Mock low confidence from System 1
    mock_reasoner.reason.return_value = ReasoningResponse(
        suggestions=["def func(): pass"],
        confidence=0.60,  # Below threshold
        reasoning="Low confidence reasoning",
        latency_ms=150.0,
        model="llama3.2:3b",
    )

    result = await coordinator.process(
        task_type="refactor",
        description="Refactor this",
        code_context="def func(): pass",
        language="python",
        mode=ProcessingMode.ADAPTIVE,
    )

    # Should escalate to System 2
    assert coordinator.escalations > 0
    mock_verifier.verify.assert_called_once()


@pytest.mark.asyncio
async def test_adaptive_mode_high_confidence_skip_verification(
    coordinator, mock_reasoner, mock_verifier
):
    """Test adaptive mode skips verification on high confidence + low complexity"""
    # Mock high confidence from System 1
    mock_reasoner.reason.return_value = ReasoningResponse(
        suggestions=["def func(): pass"],
        confidence=0.90,  # Above threshold
        reasoning="High confidence reasoning",
        latency_ms=150.0,
        model="llama3.2:3b",
    )

    result = await coordinator.process(
        task_type="explain",  # Simple task
        description="Explain this simple function",
        code_context="def hello(): pass",
        language="python",
        mode=ProcessingMode.ADAPTIVE,
    )

    # Should NOT call verifier
    assert result["verification_skipped"] is True
    mock_verifier.verify.assert_not_called()


@pytest.mark.asyncio
async def test_confidence_combination(coordinator):
    """Test confidence score combination logic"""
    # Test verified case
    combined = coordinator._combine_confidence(0.8, 0.9, verified=True)
    assert 0.85 <= combined <= 0.90  # Weighted toward System 2

    # Test failed verification
    combined = coordinator._combine_confidence(0.8, 0.9, verified=False)
    assert combined < 0.8  # Should be penalized


@pytest.mark.asyncio
async def test_suggestion_merging(coordinator):
    """Test suggestion merging logic"""
    system1_suggestions = ["suggestion 1", "suggestion 2"]
    system2_suggestions = ["suggestion 2", "suggestion 3"]

    # Verified case
    merged = coordinator._merge_suggestions(system1_suggestions, system2_suggestions, verified=True)
    assert len(merged) == 3  # Unique suggestions
    assert "suggestion 1" in merged
    assert "suggestion 3" in merged

    # Failed verification
    merged = coordinator._merge_suggestions(
        system1_suggestions, system2_suggestions, verified=False
    )
    assert merged == system2_suggestions


@pytest.mark.asyncio
async def test_performance_metrics_tracking(coordinator, mock_reasoner, mock_verifier):
    """Test performance metrics are tracked"""
    await coordinator.process(
        task_type="refactor",
        description="Test task",
        code_context="def test(): pass",
        language="python",
        mode=ProcessingMode.DUAL_PROCESS,
    )

    stats = coordinator.get_stats()
    assert stats["total_requests"] == 1
    assert stats["dual_process_count"] == 1
    assert "system1_stats" in stats
    assert "system2_stats" in stats
    assert "graph_state" in stats


@pytest.mark.asyncio
async def test_error_handling(coordinator, mock_reasoner):
    """Test error handling in coordinator"""
    # Mock System 1 failure
    mock_reasoner.reason.side_effect = Exception("Ollama connection failed")

    result = await coordinator.process(
        task_type="refactor",
        description="Test task",
        code_context="def test(): pass",
        language="python",
    )

    assert result["success"] is False
    assert "error" in result
    assert "Ollama connection failed" in result["error"]


@pytest.mark.asyncio
async def test_strategy_determination(coordinator):
    """Test strategy determination logic"""
    # ADAPTIVE mode should stay as ADAPTIVE (decision made at runtime)
    strategy = coordinator._determine_strategy(
        ProcessingMode.ADAPTIVE, complexity=0.3, task_analysis={"requires_verification": False}
    )
    assert strategy == ProcessingMode.ADAPTIVE

    # ADAPTIVE mode with high complexity should also stay ADAPTIVE
    strategy = coordinator._determine_strategy(
        ProcessingMode.ADAPTIVE, complexity=0.8, task_analysis={"requires_verification": True}
    )
    assert strategy == ProcessingMode.ADAPTIVE

    # Forced mode should be preserved
    strategy = coordinator._determine_strategy(
        ProcessingMode.SYSTEM1_ONLY, complexity=0.8, task_analysis={"requires_verification": True}
    )
    assert strategy == ProcessingMode.SYSTEM1_ONLY


@pytest.mark.asyncio
async def test_close_resources(coordinator, mock_reasoner, mock_verifier):
    """Test resource cleanup"""
    await coordinator.close()
    mock_reasoner.close.assert_called_once()
    mock_verifier.close.assert_called_once()


@pytest.mark.asyncio
async def test_metadata_in_result(coordinator):
    """Test that results include proper metadata"""
    result = await coordinator.process(
        task_type="explain", description="Test", code_context="def test(): pass", language="python"
    )

    assert "metadata" in result
    metadata = result["metadata"]
    assert "total_latency_ms" in metadata
    assert "strategy" in metadata
    assert "complexity" in metadata
    assert "intent" in metadata
    assert "task_analysis" in metadata


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
