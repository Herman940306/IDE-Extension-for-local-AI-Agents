"""
Integration tests for Dual-Process System
Project Creator: Herman Swanepoel

Tests the full integration of System 1 + System 2 with real Ollama models.
Requires Ollama to be running with llama3.2:3b and mistral:7b models.
"""

import pytest
import asyncio
from src.orchestrator.dual_process_integration import DualProcessSystem
from src.orchestrator.reasoning_coordinator import ProcessingMode


@pytest.fixture
async def dual_system():
    """Create DualProcessSystem instance"""
    system = DualProcessSystem(
        ollama_url="http://localhost:11434",
        reasoner_model="llama3.2:3b",
        verifier_model="mistral:7b"
    )
    yield system
    await system.close()


@pytest.mark.integration
@pytest.mark.asyncio
async def test_simple_explanation_system1_only(dual_system):
    """Test simple explanation using System 1 only"""
    result = await dual_system.process(
        task_type="explain",
        description="Explain what this function does",
        code_context="""
def fibonacci(n):
    if n <= 1:
        return n
    return fibonacci(n-1) + fibonacci(n-2)
""",
        language="python",
        mode=ProcessingMode.SYSTEM1_ONLY
    )
    
    assert result["success"] is True
    assert len(result["suggestions"]) > 0
    assert result["verification_skipped"] is True
    assert result["metadata"]["total_latency_ms"] < 500  # Should be fast


@pytest.mark.integration
@pytest.mark.asyncio
async def test_complex_refactor_dual_process(dual_system):
    """Test complex refactoring using dual-process"""
    result = await dual_system.process(
        task_type="refactor",
        description="Refactor this code to be more efficient",
        code_context="""
def find_duplicates(arr):
    duplicates = []
    for i in range(len(arr)):
        for j in range(i+1, len(arr)):
            if arr[i] == arr[j] and arr[i] not in duplicates:
                duplicates.append(arr[i])
    return duplicates
""",
        language="python",
        mode=ProcessingMode.DUAL_PROCESS
    )
    
    assert result["success"] is True
    assert result["system1_response"] is not None
    assert result["system2_response"] is not None
    assert "verification_passed" in result


@pytest.mark.integration
@pytest.mark.asyncio
async def test_adaptive_mode_escalation(dual_system):
    """Test adaptive mode with automatic escalation"""
    result = await dual_system.process(
        task_type="debug",
        description="Find and fix the bug in this code",
        code_context="""
def calculate_average(numbers):
    total = 0
    for num in numbers:
        total += num
    return total / len(numbers)  # Bug: division by zero if empty list
""",
        language="python",
        mode=ProcessingMode.ADAPTIVE
    )
    
    assert result["success"] is True
    # Complex debugging task should trigger System 2
    assert result["metadata"]["complexity"] > 0.5


@pytest.mark.integration
@pytest.mark.asyncio
async def test_statistics_tracking(dual_system):
    """Test that statistics are properly tracked"""
    # Process multiple requests
    for i in range(3):
        await dual_system.process(
            task_type="explain",
            description=f"Explain function {i}",
            code_context=f"def func{i}(): pass",
            language="python"
        )
    
    stats = dual_system.get_stats()
    assert stats["total_requests"] == 3
    assert "system1_stats" in stats
    assert "system2_stats" in stats
    assert stats["system1_stats"]["total_requests"] == 3


@pytest.mark.integration
@pytest.mark.asyncio
async def test_graph_state_updates(dual_system):
    """Test that meta-controller graph is updated"""
    await dual_system.process(
        task_type="refactor",
        description="Test task",
        code_context="def test(): pass",
        language="python",
        mode=ProcessingMode.DUAL_PROCESS
    )
    
    graph_state = dual_system.get_graph_state()
    assert "nodes" in graph_state
    assert "edges" in graph_state
    assert graph_state["total_executions"] > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-m", "integration"])
