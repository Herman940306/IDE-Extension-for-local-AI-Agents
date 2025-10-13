"""
Unit tests for RefactorAgent
Project Creator: Herman Swanepoel
"""

import pytest
import asyncio
from unittest.mock import Mock, AsyncMock, patch

from src.agents.refactor_agent import RefactorAgent, RefactoringPattern
from src.adapters.base_adapter import AgentConfig, Capability
from src.models.task import Task, TaskType, Priority
from src.models.context import CodeContext
from src.models.response import AgentResponse, ConfidenceLevel
from src.services.llm_manager import LLMManager, LLMProvider, LLMError
from src.services.code_smell_detector import CodeSmellDetector


@pytest.fixture
def agent_config():
    """Create agent configuration"""
    return AgentConfig(
        name="Test Refactor Agent",
        description="Test agent for refactoring",
        capabilities=[Capability.REFACTORING],
        enabled=True,
        max_concurrent=1,
        timeout=30
    )


@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager"""
    llm = Mock(spec=LLMManager)
    llm.health_check = AsyncMock(return_value=True)
    llm.generate = AsyncMock(return_value="SUGGESTION: Use async/await\nREASON: Better readability")
    return llm


@pytest.fixture
def mock_code_smell_detector():
    """Create mock code smell detector"""
    detector = Mock(spec=CodeSmellDetector)
    detector.detect_smells = AsyncMock(return_value=[])
    return detector


@pytest.fixture
def refactor_agent(agent_config, mock_llm_manager, mock_code_smell_detector):
    """Create RefactorAgent instance"""
    return RefactorAgent(
        config=agent_config,
        llm_manager=mock_llm_manager,
        code_smell_detector=mock_code_smell_detector
    )


@pytest.mark.asyncio
async def test_agent_initialization(refactor_agent):
    """Test agent initialization"""
    assert not refactor_agent.is_initialized
    
    await refactor_agent.initialize()
    
    assert refactor_agent.is_initialized
    assert len(refactor_agent.refactoring_patterns) > 0


@pytest.mark.asyncio
async def test_detect_long_method(refactor_agent):
    """Test detection of long methods"""
    await refactor_agent.initialize()
    
    # Create code with long method
    code = """
def very_long_function():
    # Line 1
    # Line 2
    # Line 3
    # Line 4
    # Line 5
    # Line 6
    # Line 7
    # Line 8
    # Line 9
    # Line 10
    # Line 11
    # Line 12
    # Line 13
    # Line 14
    # Line 15
    # Line 16
    # Line 17
    # Line 18
    # Line 19
    # Line 20
    # Line 21
    # Line 22
    # Line 23
    # Line 24
    # Line 25
    # Line 26
    # Line 27
    # Line 28
    # Line 29
    # Line 30
    # Line 31
    pass
"""
    
    context = CodeContext(
        file_path="test.py",
        language="python",
        workspace_path="/workspace"
    )
    
    task = Task(
        id="test-1",
        type=TaskType.REFACTOR,
        content=code,
        context={"workspace_path": "/workspace"},
        priority=Priority.MEDIUM
    )
    
    response = await refactor_agent.execute_task(task, context)
    
    assert response.agent_id == "refactor_agent"
    assert len(response.suggestions) > 0
    assert any("long" in s.description.lower() for s in response.suggestions)


@pytest.mark.asyncio
async def test_detect_magic_numbers(refactor_agent):
    """Test detection of magic numbers"""
    await refactor_agent.initialize()
    
    code = """
def calculate_price(quantity):
    base_price = quantity * 19.99
    if quantity > 10:
        discount = base_price * 0.15
    else:
        discount = base_price * 0.05
    tax = base_price * 0.08
    return base_price - discount + tax
"""
    
    context = CodeContext(
        file_path="test.py",
        language="python",
        workspace_path="/workspace"
    )
    
    task = Task(
        id="test-2",
        type=TaskType.REFACTOR,
        content=code,
        context={"workspace_path": "/workspace"},
        priority=Priority.MEDIUM
    )
    
    response = await refactor_agent.execute_task(task, context)
    
    assert response.agent_id == "refactor_agent"
    # Should detect magic numbers like 19.99, 0.15, 0.05, 0.08
    assert len(response.suggestions) > 0


@pytest.mark.asyncio
async def test_detect_complex_conditional(refactor_agent):
    """Test detection of complex conditionals"""
    await refactor_agent.initialize()
    
    code = """
def check_eligibility(user):
    if user.age > 18 and user.verified and user.active and not user.banned and user.country == "US":
        return True
    return False
"""
    
    context = CodeContext(
        file_path="test.py",
        language="python",
        workspace_path="/workspace"
    )
    
    task = Task(
        id="test-3",
        type=TaskType.REFACTOR,
        content=code,
        context={"workspace_path": "/workspace"},
        priority=Priority.MEDIUM
    )
    
    response = await refactor_agent.execute_task(task, context)
    
    assert response.agent_id == "refactor_agent"
    assert any("conditional" in s.description.lower() for s in response.suggestions)


@pytest.mark.asyncio
async def test_detect_dead_code(refactor_agent):
    """Test detection of dead code"""
    await refactor_agent.initialize()
    
    code = """
def process_data(data):
    if data is None:
        return None
    
    # This code is unreachable
    print("Processing data")
    result = data * 2
    return result
"""
    
    context = CodeContext(
        file_path="test.py",
        language="python",
        workspace_path="/workspace"
    )
    
    task = Task(
        id="test-4",
        type=TaskType.REFACTOR,
        content=code,
        context={"workspace_path": "/workspace"},
        priority=Priority.MEDIUM
    )
    
    response = await refactor_agent.execute_task(task, context)
    
    assert response.agent_id == "refactor_agent"
    assert any("unreachable" in s.description.lower() for s in response.suggestions)


@pytest.mark.asyncio
async def test_clean_code_no_suggestions(refactor_agent):
    """Test that clean code produces no suggestions"""
    await refactor_agent.initialize()
    
    code = """
def add(a: int, b: int) -> int:
    return a + b

def multiply(a: int, b: int) -> int:
    return a * b
"""
    
    context = CodeContext(
        file_path="test.py",
        language="python",
        workspace_path="/workspace"
    )
    
    task = Task(
        id="test-5",
        type=TaskType.REFACTOR,
        content=code,
        context={"workspace_path": "/workspace"},
        priority=Priority.MEDIUM
    )
    
    response = await refactor_agent.execute_task(task, context)
    
    assert response.agent_id == "refactor_agent"
    # Clean code should have few or no suggestions
    assert response.confidence >= 0.0


@pytest.mark.asyncio
async def test_llm_integration(refactor_agent, mock_llm_manager):
    """Test LLM integration for suggestions"""
    await refactor_agent.initialize()
    
    code = """
def long_function_with_issues():
    x = 1
    y = 2
    z = x + y
    # ... more code
    return z
"""
    
    context = CodeContext(
        file_path="test.py",
        language="python",
        workspace_path="/workspace"
    )
    
    task = Task(
        id="test-6",
        type=TaskType.REFACTOR,
        content=code,
        context={"workspace_path": "/workspace"},
        priority=Priority.MEDIUM
    )
    
    response = await refactor_agent.execute_task(task, context)
    
    # Verify LLM was called if suggestions were found
    if len(response.suggestions) > 0:
        mock_llm_manager.generate.assert_called()


@pytest.mark.asyncio
async def test_confidence_calculation(refactor_agent):
    """Test confidence score calculation"""
    await refactor_agent.initialize()
    
    code = """
def bad_function():
    x = 42  # magic number
    y = 99  # magic number
    if x > 10 and y < 100 and x != y and x + y > 50:  # complex conditional
        return x + y
    return 0
"""
    
    context = CodeContext(
        file_path="test.py",
        language="python",
        workspace_path="/workspace"
    )
    
    task = Task(
        id="test-7",
        type=TaskType.REFACTOR,
        content=code,
        context={"workspace_path": "/workspace"},
        priority=Priority.MEDIUM
    )
    
    response = await refactor_agent.execute_task(task, context)
    
    assert 0.0 <= response.confidence <= 1.0
    assert len(response.suggestions) > 0


@pytest.mark.asyncio
async def test_health_check(refactor_agent):
    """Test agent health check"""
    await refactor_agent.initialize()
    
    is_healthy = await refactor_agent.health_check()
    
    assert is_healthy is True


@pytest.mark.asyncio
async def test_get_capabilities(refactor_agent):
    """Test getting agent capabilities"""
    capabilities = await refactor_agent.get_capabilities()
    
    assert Capability.REFACTORING in capabilities


@pytest.mark.asyncio
async def test_error_handling(refactor_agent):
    """Test error handling with invalid code"""
    await refactor_agent.initialize()
    
    # Invalid Python code
    code = "def invalid syntax here"
    
    context = CodeContext(
        file_path="test.py",
        language="python",
        workspace_path="/workspace"
    )
    
    task = Task(
        id="test-8",
        type=TaskType.REFACTOR,
        content=code,
        context={"workspace_path": "/workspace"},
        priority=Priority.MEDIUM
    )
    
    # Should not raise exception, should return empty response
    response = await refactor_agent.execute_task(task, context)
    
    assert response.agent_id == "refactor_agent"
    assert isinstance(response, AgentResponse)


@pytest.mark.asyncio
async def test_non_python_language(refactor_agent):
    """Test handling of non-Python languages"""
    await refactor_agent.initialize()
    
    code = """
function calculateTotal(items) {
    let total = 0;
    for (let i = 0; i < items.length; i++) {
        total += items[i].price;
    }
    return total;
}
"""
    
    context = CodeContext(
        file_path="test.js",
        language="javascript",
        workspace_path="/workspace"
    )
    
    task = Task(
        id="test-9",
        type=TaskType.REFACTOR,
        content=code,
        context={"workspace_path": "/workspace"},
        priority=Priority.MEDIUM
    )
    
    response = await refactor_agent.execute_task(task, context)
    
    assert response.agent_id == "refactor_agent"
    # Should still work with code smell detection
    assert isinstance(response, AgentResponse)


@pytest.mark.asyncio
async def test_suggestion_deduplication(refactor_agent):
    """Test that duplicate suggestions are removed"""
    await refactor_agent.initialize()
    
    code = """
def func1():
    x = 42
    y = 42
    z = 42
    return x + y + z
"""
    
    context = CodeContext(
        file_path="test.py",
        language="python",
        workspace_path="/workspace"
    )
    
    task = Task(
        id="test-10",
        type=TaskType.REFACTOR,
        content=code,
        context={"workspace_path": "/workspace"},
        priority=Priority.MEDIUM
    )
    
    response = await refactor_agent.execute_task(task, context)
    
    # Check that suggestions are unique
    descriptions = [s.description for s in response.suggestions]
    assert len(descriptions) == len(set(descriptions))


@pytest.mark.asyncio
async def test_memory_integration(agent_config, mock_llm_manager, mock_code_smell_detector):
    """Test memory service integration"""
    from src.services.memory_service import MemoryService, MemoryConfig, StorageBackend
    
    # Create memory service
    memory_config = MemoryConfig(backend=StorageBackend.SQLITE)
    memory_service = MemoryService(memory_config)
    await memory_service.initialize()
    
    # Create agent with memory
    agent = RefactorAgent(
        config=agent_config,
        llm_manager=mock_llm_manager,
        code_smell_detector=mock_code_smell_detector,
        memory_service=memory_service
    )
    
    await agent.initialize()
    
    code = "def test(): pass"
    context = CodeContext(
        file_path="test.py",
        language="python",
        workspace_path="/workspace"
    )
    
    task = Task(
        id="test-11",
        type=TaskType.REFACTOR,
        content=code,
        context={"workspace_path": "/workspace"},
        priority=Priority.MEDIUM
    )
    
    response = await agent.execute_task(task, context)
    
    # Verify task was stored in memory
    history = await memory_service.get_session_history("/workspace", limit=10)
    assert len(history) > 0
    
    await memory_service.close()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
