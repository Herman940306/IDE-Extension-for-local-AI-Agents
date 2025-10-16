"""
Integration tests for AutoGPT adapter
Project Creator: Herman Swanepoel
"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from src.adapters.autogpt_adapter import AutoGPTAdapter, AutoGPTResearchAgent
from src.adapters.base_adapter import AgentConfig, Capability
from src.models import CodeContext, ConfidenceLevel, Priority, Suggestion, Task, TaskType


@pytest.fixture
def mock_config():
    """Create mock agent configuration"""
    return AgentConfig(
        name="Test AutoGPT Agent",
        description="Test agent",
        capabilities=[Capability.RESEARCH],
        enabled=True,
        max_concurrent=1,
        timeout=120,
        metadata={"autogpt_url": "http://localhost:8002", "model": "gpt-4", "max_iterations": 15},
    )


@pytest.fixture
def mock_task():
    """Create mock task"""
    return Task(
        id="test-task-2",
        type=TaskType.RESEARCH,
        content="def foo():\n    return 'bar'",
        context={"workspace_path": "/tmp/workspace"},
        priority=Priority.MEDIUM,
        description="Research best practices",
    )


@pytest.fixture
def mock_context():
    """Create mock code context"""
    return CodeContext(
        file_path="research.py",
        language="python",
        code="# Research code",
        workspace_path="/tmp/workspace",
        selected_text=None,
        cursor_position={"line": 0, "character": 0},
        git_branch="main",
    )


class TestAutoGPTAdapter:
    """Test suite for AutoGPTAdapter"""

    @pytest.mark.asyncio
    async def test_initialization(self, mock_config):
        """Test adapter initialization"""
        adapter = AutoGPTAdapter(mock_config)

        with patch("src.adapters.autogpt_adapter.httpx.AsyncClient") as mock_client_cls:
            mock_client = AsyncMock()
            mock_response = MagicMock()
            mock_response.json.return_value = {
                "agent_id": "autogpt-agent-456",
                "workspace_path": "/tmp/workspace",
            }
            mock_response.raise_for_status = MagicMock()
            mock_client.post = AsyncMock(return_value=mock_response)
            mock_client_cls.return_value = mock_client

            await adapter.initialize()

            assert adapter.is_initialized
            assert adapter.agent_id == "autogpt-agent-456"
            assert adapter.workspace_path == "/tmp/workspace"

    def test_get_role(self, mock_config):
        """Test role selection based on capabilities"""
        adapter = AutoGPTAdapter(mock_config)
        role = adapter._get_role()

        assert "Research" in role

    def test_get_default_goals(self, mock_config):
        """Test default goals for research agent"""
        adapter = AutoGPTAdapter(mock_config)
        goals = adapter._get_default_goals()

        assert len(goals) > 0
        assert any("research" in goal.lower() for goal in goals)

    def test_get_plugins(self, mock_config):
        """Test plugin selection"""
        adapter = AutoGPTAdapter(mock_config)
        plugins = adapter._get_plugins()

        assert "web_search" in plugins
        assert "web_scraper" in plugins

    def test_format_task(self, mock_config, mock_task, mock_context):
        """Test task formatting"""
        adapter = AutoGPTAdapter(mock_config)
        formatted = adapter._format_task(mock_task, mock_context)

        assert "Research" in formatted
        assert "research.py" in formatted
        assert "python" in formatted

    def test_parse_suggestions_with_code_blocks(self, mock_config, mock_context):
        """Test parsing suggestions from output"""
        adapter = AutoGPTAdapter(mock_config)
        output = """
Research findings:
```python
def best_practice():
    return "Use this pattern"
```
"""
        actions = []
        suggestions = adapter._parse_suggestions(output, actions, mock_context)

        assert len(suggestions) == 1
        assert "def best_practice()" in suggestions[0].code

    def test_parse_suggestions_from_file_operations(self, mock_config, mock_context):
        """Test parsing suggestions from file operations"""
        adapter = AutoGPTAdapter(mock_config)
        output = ""
        actions = [
            {
                "name": "write_file",
                "args": {"filename": "output.py", "content": "generated_content = True"},
                "reasoning": "Creating output file",
            }
        ]
        suggestions = adapter._parse_suggestions(output, actions, mock_context)

        assert len(suggestions) == 1
        assert "generated_content" in suggestions[0].code

    def test_calculate_confidence_high(self, mock_config):
        """Test confidence calculation with thorough analysis"""
        adapter = AutoGPTAdapter(mock_config)
        result = {"status": "completed", "thoughts": [{"text": f"Thought {i}"} for i in range(10)]}
        suggestions = [
            Suggestion(
                id="sugg-1",
                code="print('hello world')",
                description="Example suggestion",
                confidence=ConfidenceLevel.HIGH,
                diff=None,
                applicable_range=None,
            )
        ]

        confidence = adapter._calculate_confidence(result, suggestions)
        assert confidence >= 0.9

    def test_calculate_confidence_low(self, mock_config):
        """Test confidence calculation with minimal analysis"""
        adapter = AutoGPTAdapter(mock_config)
        result = {"status": "failed", "thoughts": []}
        suggestions = []

        confidence = adapter._calculate_confidence(result, suggestions)
        assert confidence <= 0.6

    def test_build_reasoning(self, mock_config):
        """Test reasoning generation"""
        adapter = AutoGPTAdapter(mock_config)
        thoughts = [{"text": "Analyzing requirements"}, {"text": "Researching solutions"}]
        actions = [{"name": "web_search", "reasoning": "Finding information"}]
        output = "Research complete"

        reasoning = adapter._build_reasoning(thoughts, actions, output)
        assert "AutoGPT" in reasoning
        assert "Analyzing requirements" in reasoning
        assert "web_search" in reasoning

    @pytest.mark.asyncio
    async def test_health_check_healthy(self, mock_config):
        """Test health check when adapter is healthy"""
        adapter = AutoGPTAdapter(mock_config)
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
        adapter = AutoGPTAdapter(mock_config)
        adapter.is_initialized = False

        is_healthy = await adapter.health_check()
        assert not is_healthy

    @pytest.mark.asyncio
    async def test_provide_input(self, mock_config):
        """Test providing input to AutoGPT"""
        adapter = AutoGPTAdapter(mock_config)
        adapter.http_client = AsyncMock()
        adapter.http_client.post = AsyncMock()

        await adapter._provide_input("task-123", "Continue")

        adapter.http_client.post.assert_called_once()


class TestAutoGPTResearchAgent:
    """Test suite for AutoGPTResearchAgent"""

    def test_initialization(self):
        """Test specialized research agent initialization"""
        agent = AutoGPTResearchAgent()

        assert agent.config.name == "AutoGPT Research Agent"
        assert Capability.RESEARCH in agent.config.capabilities
        assert agent.config.timeout == 180

    def test_capabilities(self):
        """Test research agent has correct capabilities"""
        agent = AutoGPTResearchAgent()

        assert Capability.RESEARCH in agent.config.capabilities
        assert Capability.CODE_GENERATION in agent.config.capabilities
