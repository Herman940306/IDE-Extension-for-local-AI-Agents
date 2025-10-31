"""
Integration tests for SuperAGI adapter
Project Creator: Herman Swanepoel
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.adapters.base_adapter import AgentConfig, Capability
from src.adapters.superagi_adapter import SuperAGIAdapter, SuperAGICodeAgent
from src.models import (
    CodeContext,
    ConfidenceLevel,
    Priority,
    Suggestion,
    Task,
    TaskType,
)


@pytest.fixture
def mock_config():
    """Create mock agent configuration"""
    return AgentConfig(
        name="Test SuperAGI Agent",
        description="Test agent",
        capabilities=[Capability.CODE_GENERATION],
        enabled=True,
        max_concurrent=1,
        timeout=60,
        metadata={
            "superagi_url": "http://localhost:8001",
            "model": "gpt-4",
            "max_iterations": 10,
        },
    )


@pytest.fixture
def mock_task():
    """Create mock task"""
    return Task(
        id="test-task-1",
        type=TaskType.REFACTOR,
        content="Refactor the given function",
        priority=Priority.HIGH,
        description="Refactor this function",
    )


@pytest.fixture
def mock_context():
    """Create mock code context"""
    return CodeContext(
        file_path="test.py",
        language="python",
        code="def old_function():\n    pass",
        selected_text="def old_function():\n    pass",
        workspace_path="/tmp/workspace",
        cursor_position={"line": 0, "character": 0},
        git_branch="main",
    )


class TestSuperAGIAdapter:
    """Test suite for SuperAGIAdapter"""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_config):
        """Test adapter initialization"""
        adapter = SuperAGIAdapter(mock_config)

        with patch(
            "src.adapters.superagi_adapter.httpx.AsyncClient"
        ) as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {"agent_id": "test-agent-123"}
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            await adapter.initialize()

            assert adapter.is_initialized
            assert adapter.agent_id == "test-agent-123"

    def test_get_default_goals(self, mock_config):
        """Test default goals generation"""
        adapter = SuperAGIAdapter(mock_config)
        goals = adapter._get_default_goals()

        assert len(goals) > 0
        assert any("code" in goal.lower() for goal in goals)

    def test_get_tools(self, mock_config):
        """Test tools selection based on capabilities"""
        adapter = SuperAGIAdapter(mock_config)
        tools = adapter._get_tools()

        assert "code_analysis" in tools
        assert "code_generator" in tools

    def test_extract_goal(self, mock_config, mock_task, mock_context):
        """Test goal extraction from task"""
        adapter = SuperAGIAdapter(mock_config)
        goal = adapter._extract_goal(mock_task, mock_context)

        assert "Refactor" in goal
        assert "test.py" in goal
        assert "python" in goal

    def test_parse_suggestions_with_code_blocks(self, mock_config):
        """Test parsing suggestions from output"""
        adapter = SuperAGIAdapter(mock_config)
        output = """
Here is the refactored code:
```python
def new_function():
    return True
```
"""
        steps = []
        suggestions = adapter._parse_suggestions(output, steps)

        assert len(suggestions) == 1
        assert "def new_function()" in suggestions[0].code

    def test_parse_suggestions_from_steps(self, mock_config):
        """Test parsing suggestions from execution steps"""
        adapter = SuperAGIAdapter(mock_config)
        output = ""
        steps = [
            {
                "tool": "code_generator",
                "output": "```python\ngenerated_code()\n```",
                "thought": "Generated solution",
                "step_number": 1,
            }
        ]
        suggestions = adapter._parse_suggestions(output, steps)

        assert len(suggestions) == 1
        assert "generated_code()" in suggestions[0].code

    def test_calculate_confidence_high(self, mock_config):
        """Test confidence calculation for successful execution"""
        adapter = SuperAGIAdapter(mock_config)
        result = {
            "status": "completed",
            "steps": [{"status": "success"}, {"status": "success"}],
        }
        suggestions = [
            Suggestion(
                id="sugg-1",
                code="def new_function():\n    return True",
                description="Example suggestion",
                confidence=ConfidenceLevel.HIGH,
                diff=None,
                applicable_range=None,
            )
        ]

        confidence = adapter._calculate_confidence(result, suggestions)
        assert confidence >= 0.9

    def test_calculate_confidence_low(self, mock_config):
        """Test confidence calculation for failed execution"""
        adapter = SuperAGIAdapter(mock_config)
        result = {"status": "failed", "steps": []}
        suggestions = []

        confidence = adapter._calculate_confidence(result, suggestions)
        assert confidence <= 0.6

    def test_build_reasoning(self, mock_config):
        """Test reasoning generation from steps"""
        adapter = SuperAGIAdapter(mock_config)
        steps = [
            {"tool": "analyzer", "thought": "Analyzing", "status": "success"},
            {"tool": "generator", "thought": "Generating", "status": "success"},
        ]
        output = "Final result"

        reasoning = adapter._build_reasoning(steps, output)
        assert "SuperAGI" in reasoning
        assert "analyzer" in reasoning
        assert "Final result" in reasoning

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_config):
        """Test health check when adapter is healthy"""
        adapter = SuperAGIAdapter(mock_config)
        adapter.is_initialized = True
        adapter.http_client = AsyncMock()

        mock_response = AsyncMock()
        mock_response.status_code = 200
        adapter.http_client.get = AsyncMock(return_value=mock_response)

        is_healthy = await adapter.health_check()
        assert is_healthy

    @pytest.mark.asyncio
    async def test_health_check_unhealthy(self, mock_config):
        """Test health check when adapter is unhealthy"""
        adapter = SuperAGIAdapter(mock_config)
        adapter.is_initialized = False

        is_healthy = await adapter.health_check()
        assert not is_healthy


class TestSuperAGICodeAgent:
    """Test suite for SuperAGICodeAgent"""

    def test_initialization(self):
        """Test specialized code agent initialization"""
        agent = SuperAGICodeAgent()

        assert agent.config.name == "SuperAGI Code Agent"
        assert Capability.CODE_GENERATION in agent.config.capabilities
        assert agent.config.timeout == 120

    def test_capabilities(self):
        """Test code agent has correct capabilities"""
        agent = SuperAGICodeAgent()

        assert Capability.CODE_GENERATION in agent.config.capabilities
        assert Capability.REFACTORING in agent.config.capabilities
