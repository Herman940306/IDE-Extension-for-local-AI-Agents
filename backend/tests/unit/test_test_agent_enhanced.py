"""
Comprehensive tests for TestAgent with improved coverage
Project Creator: Herman Swanepoel
Coverage Target: 32% → 70%+
"""

from unittest.mock import AsyncMock

import pytest
from src.adapters.base_adapter import AgentConfig, Capability
from src.agents.test_agent import TestAgent
from src.models.context import CodeContext
from src.models.response import AgentResponse, ConfidenceLevel, Suggestion
from src.models.task import Priority, Task, TaskType
from src.services.llm_manager import LLMManager


@pytest.fixture
def mock_llm_manager():
    """Create a mock LLM manager"""
    llm = AsyncMock(spec=LLMManager)
    llm.generate = AsyncMock(
        return_value="# Generated test code\ndef test_example():\n    assert True"
    )
    llm.health_check = AsyncMock(return_value=True)
    return llm


@pytest.fixture
def test_agent_config():
    """Create test agent configuration"""
    return AgentConfig(
        name="Test Generation Agent",
        description="Generates comprehensive tests",
        capabilities=[Capability.TESTING],
        metadata={"supports": ["unit", "edge", "integration"]},
    )


@pytest.fixture
def test_agent(mock_llm_manager, test_agent_config):
    """Create test agent instance"""
    return TestAgent(llm_manager=mock_llm_manager, config=test_agent_config)


class TestTestAgentInitialization:
    """Tests for TestAgent initialization"""

    def test_init_with_config(self, mock_llm_manager, test_agent_config):
        """Test initialization with provided config"""
        agent = TestAgent(llm_manager=mock_llm_manager, config=test_agent_config)
        assert agent.config.name == "Test Generation Agent"
        assert Capability.TESTING in agent.config.capabilities
        assert agent.llm_manager == mock_llm_manager

    def test_init_default_config(self, mock_llm_manager):
        """Test initialization with default config"""
        agent = TestAgent(llm_manager=mock_llm_manager)
        assert agent.config is not None
        assert agent.config.name == "Test Generation Agent"
        assert Capability.TESTING in agent.config.capabilities
        assert "supports" in agent.config.metadata

    @pytest.mark.asyncio
    async def test_initialize(self, test_agent):
        """Test initialize method"""
        await test_agent.initialize()
        # Should complete without error
        assert True

    @pytest.mark.asyncio
    async def test_get_capabilities(self, test_agent):
        """Test get_capabilities method"""
        capabilities = await test_agent.get_capabilities()
        assert isinstance(capabilities, list)
        assert Capability.TESTING in capabilities


class TestFrameworkDetermination:
    """Tests for test framework determination"""

    def test_determine_framework_python(self, test_agent):
        """Test framework determination for Python"""
        framework = test_agent._determine_test_framework("python")
        assert framework == "pytest"

    def test_determine_framework_javascript(self, test_agent):
        """Test framework determination for JavaScript"""
        framework = test_agent._determine_test_framework("javascript")
        assert framework == "jest"

    def test_determine_framework_typescript(self, test_agent):
        """Test framework determination for TypeScript"""
        framework = test_agent._determine_test_framework("typescript")
        assert framework == "jest"

    def test_determine_framework_java(self, test_agent):
        """Test framework determination for Java"""
        framework = test_agent._determine_test_framework("java")
        assert framework == "junit"

    def test_determine_framework_go(self, test_agent):
        """Test framework determination for Go"""
        framework = test_agent._determine_test_framework("go")
        assert framework == "testing"

    def test_determine_framework_rust(self, test_agent):
        """Test framework determination for Rust"""
        framework = test_agent._determine_test_framework("rust")
        assert framework == "cargo test"

    def test_determine_framework_unknown(self, test_agent):
        """Test framework determination for unknown language"""
        framework = test_agent._determine_test_framework("unknown_lang")
        assert framework == "generic"


class TestIntegrationDetection:
    """Tests for integration test needs detection"""

    def test_needs_integration_requests(self, test_agent):
        """Test detection of requests import"""
        code = "import requests\ndef fetch(): pass"
        assert test_agent._needs_integration_test(code) is True

    def test_needs_integration_httpx(self, test_agent):
        """Test detection of httpx import"""
        code = "import httpx\nasync def get(): pass"
        assert test_agent._needs_integration_test(code) is True

    def test_needs_integration_fetch(self, test_agent):
        """Test detection of fetch calls"""
        code = "async function getData() { return await fetch(url); }"
        assert test_agent._needs_integration_test(code) is True

    def test_needs_integration_axios(self, test_agent):
        """Test detection of axios usage"""
        code = "const response = await axios.get('/api/data');"
        assert test_agent._needs_integration_test(code) is True

    def test_needs_integration_database(self, test_agent):
        """Test detection of database operations"""
        code = "def save(): database.query('INSERT INTO...')"
        assert test_agent._needs_integration_test(code) is True

    def test_needs_integration_api_keyword(self, test_agent):
        """Test detection of API keyword"""
        code = "def call_api(): return api.request()"
        assert test_agent._needs_integration_test(code) is True

    def test_no_integration_needed(self, test_agent):
        """Test simple code without integration needs"""
        code = "def add(a, b): return a + b"
        assert test_agent._needs_integration_test(code) is False


class TestTestGeneration:
    """Tests for test generation methods"""

    @pytest.mark.asyncio
    async def test_generate_unit_tests_success(self, test_agent, mock_llm_manager):
        """Test successful unit test generation"""
        mock_llm_manager.generate.return_value = "def test_add(): assert add(1, 2) == 3"

        suggestion = await test_agent._generate_unit_tests(
            "def add(a, b): return a + b", "python", "pytest"
        )

        assert suggestion is not None
        assert isinstance(suggestion, Suggestion)
        assert "test_add" in suggestion.code
        assert suggestion.confidence == ConfidenceLevel.HIGH
        assert "pytest" in suggestion.description
        assert suggestion.id.startswith("test_unit_")

    @pytest.mark.asyncio
    async def test_generate_unit_tests_failure(self, test_agent, mock_llm_manager):
        """Test unit test generation failure"""
        mock_llm_manager.generate.side_effect = Exception("LLM error")

        suggestion = await test_agent._generate_unit_tests(
            "def add(a, b): return a + b", "python", "pytest"
        )

        assert suggestion is None

    @pytest.mark.asyncio
    async def test_generate_edge_case_tests_success(self, test_agent, mock_llm_manager):
        """Test successful edge case test generation"""
        mock_llm_manager.generate.return_value = "def test_edge(): assert add(0, 0) == 0"

        suggestion = await test_agent._generate_edge_case_tests(
            "def add(a, b): return a + b", "python", "pytest"
        )

        assert suggestion is not None
        assert isinstance(suggestion, Suggestion)
        assert suggestion.confidence == ConfidenceLevel.MEDIUM
        assert "Edge case" in suggestion.description
        assert suggestion.id.startswith("test_edge_")

    @pytest.mark.asyncio
    async def test_generate_edge_case_tests_failure(self, test_agent, mock_llm_manager):
        """Test edge case test generation failure"""
        mock_llm_manager.generate.side_effect = Exception("LLM error")

        suggestion = await test_agent._generate_edge_case_tests(
            "def add(a, b): return a + b", "python", "pytest"
        )

        assert suggestion is None

    @pytest.mark.asyncio
    async def test_generate_integration_tests_success(self, test_agent, mock_llm_manager):
        """Test successful integration test generation"""
        mock_llm_manager.generate.return_value = "def test_api(): pass"

        suggestion = await test_agent._generate_integration_tests(
            "import requests\ndef fetch(): pass", "python", "pytest"
        )

        assert suggestion is not None
        assert isinstance(suggestion, Suggestion)
        assert suggestion.confidence == ConfidenceLevel.MEDIUM
        assert "Integration" in suggestion.description
        assert suggestion.id.startswith("test_integration_")

    @pytest.mark.asyncio
    async def test_generate_integration_tests_failure(self, test_agent, mock_llm_manager):
        """Test integration test generation failure"""
        mock_llm_manager.generate.side_effect = Exception("LLM error")

        suggestion = await test_agent._generate_integration_tests(
            "import requests\ndef fetch(): pass", "python", "pytest"
        )

        assert suggestion is None

    @pytest.mark.asyncio
    async def test_generate_tests_all_types(self, test_agent, mock_llm_manager):
        """Test generation of all test types"""
        mock_llm_manager.generate.return_value = "def test(): pass"

        code = "import requests\ndef fetch_data(): return requests.get('/api')"
        suggestions = await test_agent._generate_tests(code, "python", "pytest")

        # Should generate unit, edge case, and integration tests
        assert len(suggestions) == 3
        assert all(isinstance(s, Suggestion) for s in suggestions)

    @pytest.mark.asyncio
    async def test_generate_tests_no_integration(self, test_agent, mock_llm_manager):
        """Test generation without integration tests"""
        mock_llm_manager.generate.return_value = "def test(): pass"

        code = "def add(a, b): return a + b"
        suggestions = await test_agent._generate_tests(code, "python", "pytest")

        # Should generate only unit and edge case tests
        assert len(suggestions) == 2


class TestTaskExecution:
    """Tests for task execution"""

    @pytest.mark.asyncio
    async def test_execute_task_success(self, test_agent, mock_llm_manager):
        """Test successful task execution"""
        mock_llm_manager.generate.return_value = "def test(): pass"

        task = Task(
            id="1",
            type=TaskType.TEST_GENERATION,
            content="def add(a, b): return a + b",
            description="Generate tests",
            priority=Priority.HIGH,
        )

        context = CodeContext(
            file_path="test.py",
            code="def add(a, b): return a + b",
            language="python",
        )

        result = await test_agent.execute_task(task, context)

        assert isinstance(result, AgentResponse)
        assert result.agent_id == "test_agent"
        assert len(result.suggestions) == 2  # unit + edge case
        assert result.confidence > 0
        assert "pytest" in result.metadata["test_framework"]
        assert result.metadata["language"] == "python"

    @pytest.mark.asyncio
    async def test_execute_task_with_integration(self, test_agent, mock_llm_manager):
        """Test task execution with integration tests"""
        mock_llm_manager.generate.return_value = "def test(): pass"

        task = Task(
            id="2",
            type=TaskType.TEST_GENERATION,
            content="import requests\ndef fetch(): pass",
            description="Generate tests with integration",
            priority=Priority.MEDIUM,
        )

        context = CodeContext(
            file_path="api.py",
            code="import requests\ndef fetch(): return requests.get('/api')",
            language="python",
        )

        result = await test_agent.execute_task(task, context)

        assert isinstance(result, AgentResponse)
        assert len(result.suggestions) == 3  # unit + edge + integration
        assert result.confidence > 0

    @pytest.mark.asyncio
    async def test_execute_task_empty_code(self, test_agent):
        """Test task execution with empty code"""
        task = Task(
            id="3",
            type=TaskType.TEST_GENERATION,
            content="",
            description="Generate tests",
            priority=Priority.LOW,
        )

        context = CodeContext(
            file_path="test.py",
            code="",
            language="python",
        )

        result = await test_agent.execute_task(task, context)

        assert isinstance(result, AgentResponse)
        assert result.confidence == 0.0
        assert len(result.suggestions) == 0
        assert "No code provided" in result.reasoning
        assert result.metadata["error"] == "missing_code"

    @pytest.mark.asyncio
    async def test_execute_task_javascript(self, test_agent, mock_llm_manager):
        """Test task execution for JavaScript"""
        mock_llm_manager.generate.return_value = "test('adds', () => {})"

        task = Task(
            id="4",
            type=TaskType.TEST_GENERATION,
            content="function add(a, b) { return a + b; }",
            description="Generate JS tests",
            priority=Priority.MEDIUM,
        )

        context = CodeContext(
            file_path="add.js",
            code="function add(a, b) { return a + b; }",
            language="javascript",
        )

        result = await test_agent.execute_task(task, context)

        assert isinstance(result, AgentResponse)
        assert result.metadata["test_framework"] == "jest"
        assert result.metadata["language"] == "javascript"


class TestConfidenceCalculation:
    """Tests for confidence calculation"""

    def test_confidence_to_float_high(self, test_agent):
        """Test HIGH confidence conversion"""
        assert test_agent._confidence_to_float(ConfidenceLevel.HIGH) == 0.9

    def test_confidence_to_float_medium(self, test_agent):
        """Test MEDIUM confidence conversion"""
        assert test_agent._confidence_to_float(ConfidenceLevel.MEDIUM) == 0.7

    def test_confidence_to_float_low(self, test_agent):
        """Test LOW confidence conversion"""
        assert test_agent._confidence_to_float(ConfidenceLevel.LOW) == 0.4

    def test_calculate_confidence_empty(self, test_agent):
        """Test confidence calculation with empty suggestions"""
        confidence = test_agent._calculate_confidence([])
        assert confidence == 0.0

    def test_calculate_confidence_single(self, test_agent):
        """Test confidence calculation with single suggestion"""
        suggestions = [
            Suggestion(
                id="1",
                code="test",
                description="Test",
                confidence=ConfidenceLevel.HIGH,
            )
        ]
        confidence = test_agent._calculate_confidence(suggestions)
        assert confidence == 0.9

    def test_calculate_confidence_multiple(self, test_agent):
        """Test confidence calculation with multiple suggestions"""
        suggestions = [
            Suggestion(
                id="1",
                code="test1",
                description="Test 1",
                confidence=ConfidenceLevel.HIGH,
            ),
            Suggestion(
                id="2",
                code="test2",
                description="Test 2",
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ]
        confidence = test_agent._calculate_confidence(suggestions)
        assert confidence == pytest.approx(0.8, abs=0.01)  # (0.9 + 0.7) / 2


class TestReasoningBuilder:
    """Tests for reasoning text builder"""

    def test_build_reasoning_empty(self, test_agent):
        """Test reasoning with no suggestions"""
        reasoning = test_agent._build_reasoning("python", "pytest", [])
        assert "No actionable test scenarios" in reasoning

    def test_build_reasoning_with_suggestions(self, test_agent):
        """Test reasoning with suggestions"""
        suggestions = [
            Suggestion(
                id="1",
                code="test",
                description="Unit tests using pytest",
                confidence=ConfidenceLevel.HIGH,
            ),
            Suggestion(
                id="2",
                code="test",
                description="Edge case tests using pytest",
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ]
        reasoning = test_agent._build_reasoning("python", "pytest", suggestions)

        assert "Generated automated tests" in reasoning
        assert "Language: python" in reasoning
        assert "Framework: pytest" in reasoning
        assert "Unit tests using pytest" in reasoning
        assert "Edge case tests using pytest" in reasoning


class TestHelperMethods:
    """Tests for helper methods"""

    def test_new_suggestion_id_format(self, test_agent):
        """Test suggestion ID generation format"""
        test_id = test_agent._new_suggestion_id("unit")
        assert test_id.startswith("test_unit_")
        assert len(test_id) == len("test_unit_") + 8  # 8 hex chars

    def test_new_suggestion_id_unique(self, test_agent):
        """Test suggestion IDs are unique"""
        id1 = test_agent._new_suggestion_id("unit")
        id2 = test_agent._new_suggestion_id("unit")
        assert id1 != id2

    def test_create_empty_response(self, test_agent):
        """Test empty response creation"""
        task = Task(
            id="1",
            type=TaskType.TEST_GENERATION,
            content="",
            description="Test",
            priority=Priority.LOW,
        )
        response = test_agent._create_empty_response(task)

        assert response.agent_id == "test_agent"
        assert response.confidence == 0.0
        assert len(response.suggestions) == 0
        assert "No code provided" in response.reasoning
        assert response.metadata["error"] == "missing_code"

    def test_create_error_response(self, test_agent):
        """Test error response creation"""
        task = Task(
            id="2",
            type=TaskType.TEST_GENERATION,
            content="code",
            description="Test",
            priority=Priority.MEDIUM,
        )
        response = test_agent._create_error_response(task, "Test error")

        assert response.agent_id == "test_agent"
        assert response.confidence == 0.0
        assert len(response.suggestions) == 0
        assert "Test error" in response.reasoning
        assert response.metadata["error"] == "Test error"


class TestHealthCheck:
    """Tests for health check"""

    @pytest.mark.asyncio
    async def test_health_check_success(self, test_agent, mock_llm_manager):
        """Test successful health check"""
        mock_llm_manager.generate.return_value = "pong"
        result = await test_agent.health_check()
        assert result is True
        mock_llm_manager.generate.assert_called_once_with("ping", max_tokens=8)

    @pytest.mark.asyncio
    async def test_health_check_failure(self, test_agent, mock_llm_manager):
        """Test failed health check"""
        mock_llm_manager.generate.side_effect = Exception("LLM down")
        result = await test_agent.health_check()
        assert result is False


class TestIntegrationScenarios:
    """Integration tests with real-world scenarios"""

    @pytest.mark.asyncio
    async def test_complex_python_function(self, test_agent, mock_llm_manager):
        """Test with complex Python function"""
        mock_llm_manager.generate.return_value = "def test_complex(): pass"

        code = """
def calculate_statistics(data: List[float]) -> dict:
    if not data:
        raise ValueError("Empty data")
    return {
        'mean': sum(data) / len(data),
        'max': max(data),
        'min': min(data)
    }
"""
        task = Task(
            id="complex",
            type=TaskType.TEST_GENERATION,
            content=code,
            description="Test complex function",
            priority=Priority.HIGH,
        )

        context = CodeContext(file_path="stats.py", code=code, language="python")
        result = await test_agent.execute_task(task, context)

        assert result.confidence > 0
        assert len(result.suggestions) >= 2

    @pytest.mark.asyncio
    async def test_api_endpoint_code(self, test_agent, mock_llm_manager):
        """Test with API endpoint code"""
        mock_llm_manager.generate.return_value = "async def test_endpoint(): pass"

        code = """
import requests

async def fetch_user(user_id: int):
    response = await requests.get(f'/api/users/{user_id}')
    return response.json()
"""
        task = Task(
            id="api",
            type=TaskType.TEST_GENERATION,
            content=code,
            description="Test API code",
            priority=Priority.HIGH,
        )

        context = CodeContext(file_path="api.py", code=code, language="python")
        result = await test_agent.execute_task(task, context)

        # Should include integration tests
        assert len(result.suggestions) == 3
        assert result.metadata["test_count"] == 3
