"""
Comprehensive tests for BugAgent - targeting 88%+ coverage
"""

from unittest.mock import AsyncMock, Mock

import pytest
from src.agents.bug_agent import BugAgent, BugCategory, Severity
from src.models import CodeContext, ConfidenceLevel, Priority, Task, TaskType
from src.services.llm_manager import LLMManager

# ============================================================================
# Fixtures
# ============================================================================


@pytest.fixture
def mock_llm_manager():
    """Create mock LLM manager"""
    manager = Mock(spec=LLMManager)
    manager.generate = AsyncMock(return_value="# Fixed code\npass")
    return manager


@pytest.fixture
def bug_agent(mock_llm_manager):
    """Create BugAgent instance"""
    return BugAgent(mock_llm_manager)


@pytest.fixture
def base_task():
    """Base task fixture"""
    return Task(
        id="test-task-123",
        type=TaskType.BUG_DETECTION,
        content="Analyze code for bugs",
        context={"workspace_path": "/workspace"},
        priority=Priority.HIGH,
        description="Bug detection task",
    )


@pytest.fixture
def python_context():
    """Python code context"""
    return CodeContext(
        file_path="test.py",
        language="python",
        code="def hello():\n    return 'world'",
        workspace_path="/workspace",
        cursor_position={"line": 1, "character": 0},
        git_branch="main",
        selected_text=None,
    )


@pytest.fixture
def javascript_context():
    """JavaScript code context"""
    return CodeContext(
        file_path="test.js",
        language="javascript",
        code="function hello() {\n  return 'world';\n}",
        workspace_path="/workspace",
        cursor_position={"line": 1, "character": 0},
        git_branch="main",
        selected_text=None,
    )


# ============================================================================
# Test Initialization
# ============================================================================


class TestBugAgentInitialization:
    """Test BugAgent initialization"""

    def test_initialization(self, mock_llm_manager):
        """Test agent initializes correctly"""
        agent = BugAgent(mock_llm_manager)

        assert agent.llm_manager == mock_llm_manager
        assert agent.name == "Bug Agent"
        assert "sql_injection" in agent.security_patterns
        assert "command_injection" in agent.security_patterns
        assert "nested_loops" in agent.performance_patterns

    def test_security_patterns_defined(self, bug_agent):
        """Test security patterns are properly defined"""
        expected_patterns = [
            "sql_injection",
            "command_injection",
            "hardcoded_secret",
            "xss_vulnerability",
            "path_traversal",
            "insecure_random",
        ]

        for pattern in expected_patterns:
            assert pattern in bug_agent.security_patterns

    def test_performance_patterns_defined(self, bug_agent):
        """Test performance patterns are properly defined"""
        expected_patterns = [
            "nested_loops",
            "inefficient_string_concat",
            "global_variable",
        ]

        for pattern in expected_patterns:
            assert pattern in bug_agent.performance_patterns


# ============================================================================
# Test Static Analysis - Security Patterns
# ============================================================================


class TestSecurityPatternDetection:
    """Test security vulnerability detection"""

    @pytest.mark.asyncio
    async def test_sql_injection_detection(self, bug_agent, base_task):
        """Test SQL injection pattern detection"""
        context = CodeContext(
            file_path="db.py",
            language="python",
            code='cursor.execute("SELECT * FROM users WHERE id=%s" % user_id)',
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        assert response.agent_id == "bug_agent"
        assert response.metadata["static_issues"] >= 1
        # Should detect SQL injection
        assert any("SQL injection" in s.description for s in response.suggestions)

    @pytest.mark.asyncio
    async def test_command_injection_detection(self, bug_agent, base_task):
        """Test command injection detection"""
        context = CodeContext(
            file_path="exec.py",
            language="python",
            code="import os\nos.system(user_input)",
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        assert response.metadata["static_issues"] >= 1
        assert any(
            "command injection" in s.description.lower() for s in response.suggestions
        )

    @pytest.mark.asyncio
    async def test_hardcoded_secret_detection(self, bug_agent, base_task):
        """Test hardcoded secret detection"""
        context = CodeContext(
            file_path="config.py",
            language="python",
            code='api_key = "sk-1234567890abcdef"',
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        assert response.metadata["static_issues"] >= 1
        assert any("secret" in s.description.lower() for s in response.suggestions)

    @pytest.mark.asyncio
    async def test_xss_vulnerability_detection(self, bug_agent, base_task):
        """Test XSS vulnerability detection"""
        context = CodeContext(
            file_path="app.js",
            language="javascript",
            code="element.innerHTML = userInput;",
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        assert response.metadata["static_issues"] >= 1
        assert any("XSS" in s.description for s in response.suggestions)

    @pytest.mark.asyncio
    async def test_path_traversal_detection(self, bug_agent, base_task):
        """Test path traversal detection"""
        context = CodeContext(
            file_path="file.py",
            language="python",
            code='open("/base/" + user_path)',
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        assert response.metadata["static_issues"] >= 1
        assert any(
            "path traversal" in s.description.lower() for s in response.suggestions
        )

    @pytest.mark.asyncio
    async def test_insecure_random_detection(self, bug_agent, base_task):
        """Test insecure random detection"""
        context = CodeContext(
            file_path="crypto.py",
            language="python",
            code="import random\ntoken = random.random()",
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        assert response.metadata["static_issues"] >= 1
        assert any("random" in s.description.lower() for s in response.suggestions)


# ============================================================================
# Test Static Analysis - Performance Patterns
# ============================================================================


class TestPerformancePatternDetection:
    """Test performance issue detection"""

    @pytest.mark.asyncio
    async def test_nested_loops_detection(self, bug_agent, base_task):
        """Test nested loops detection"""
        context = CodeContext(
            file_path="loops.py",
            language="python",
            code="for i in range(10):\n    for j in range(10):\n        pass",
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        assert response.metadata["static_issues"] >= 1
        assert any(
            "nested loops" in s.description.lower() for s in response.suggestions
        )

    @pytest.mark.asyncio
    async def test_inefficient_string_concat_detection(self, bug_agent, base_task):
        """Test inefficient string concatenation detection"""
        context = CodeContext(
            file_path="string.py",
            language="python",
            code='result = ""\nresult += "test"',
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        assert response.metadata["static_issues"] >= 1
        assert any(
            "string" in s.description.lower() or "concat" in s.description.lower()
            for s in response.suggestions
        )

    @pytest.mark.asyncio
    async def test_global_variable_detection(self, bug_agent, base_task):
        """Test global variable detection"""
        context = CodeContext(
            file_path="globals.py",
            language="python",
            code="global counter\ncounter = 0",
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        assert response.metadata["static_issues"] >= 1
        assert any("global" in s.description.lower() for s in response.suggestions)


# ============================================================================
# Test Language-Specific Checks
# ============================================================================


class TestLanguageSpecificChecks:
    """Test language-specific security and quality checks"""

    @pytest.mark.asyncio
    async def test_python_pickle_detection(self, bug_agent, base_task):
        """Test Python pickle usage detection"""
        context = CodeContext(
            file_path="serialize.py",
            language="python",
            code="import pickle\ndata = pickle.loads(untrusted_data)",
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        assert response.metadata["static_issues"] >= 1
        assert any(
            "deserialization" in s.description.lower() for s in response.suggestions
        )

    @pytest.mark.asyncio
    async def test_python_assert_detection(self, bug_agent, base_task):
        """Test Python assert in production detection"""
        context = CodeContext(
            file_path="validate.py",
            language="python",
            code="assert user.is_authenticated, 'Not logged in'",
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        assert response.metadata["static_issues"] >= 1
        assert any("assert" in s.description.lower() for s in response.suggestions)

    @pytest.mark.asyncio
    async def test_javascript_loose_equality_detection(self, bug_agent, base_task):
        """Test JavaScript loose equality detection"""
        context = CodeContext(
            file_path="compare.js",
            language="javascript",
            code="if (x == y) { return true; }",
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        assert response.metadata["static_issues"] >= 1
        assert any("===" in s.description for s in response.suggestions)

    @pytest.mark.asyncio
    async def test_javascript_console_log_detection(self, bug_agent, base_task):
        """Test JavaScript console.log detection"""
        context = CodeContext(
            file_path="debug.js",
            language="javascript",
            code="console.log('Debug info:', data);",
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        assert response.metadata["static_issues"] >= 1
        assert any("console.log" in s.description.lower() for s in response.suggestions)

    @pytest.mark.asyncio
    async def test_typescript_specific_checks(self, bug_agent, base_task):
        """Test TypeScript gets JavaScript checks"""
        context = CodeContext(
            file_path="app.ts",
            language="typescript",
            code="if (value == null) { console.log('empty'); }",
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        # TypeScript should get JavaScript checks
        assert response.metadata["static_issues"] >= 1


# ============================================================================
# Test LLM Analysis
# ============================================================================


class TestLLMAnalysis:
    """Test LLM-powered analysis"""

    @pytest.mark.asyncio
    async def test_llm_analysis_success(self, bug_agent, base_task, python_context):
        """Test successful LLM analysis"""
        bug_agent.llm_manager.generate.return_value = """
ISSUE: security - high
LINE: 5
DESCRIPTION: SQL injection vulnerability
FIX: Use parameterized queries
---
ISSUE: performance - medium
LINE: 10
DESCRIPTION: Inefficient algorithm
FIX: Use hash table for O(1) lookup
---
"""

        response = await bug_agent.analyze_code(base_task, python_context)

        assert response.agent_id == "bug_agent"
        assert response.metadata["llm_issues"] >= 1
        assert response.suggestions

    @pytest.mark.asyncio
    async def test_llm_analysis_failure(self, bug_agent, base_task, python_context):
        """Test LLM analysis handles failures gracefully"""
        bug_agent.llm_manager.generate.side_effect = Exception("LLM error")

        response = await bug_agent.analyze_code(base_task, python_context)

        # Should still return response even if LLM fails
        assert response.agent_id == "bug_agent"
        assert response.metadata["llm_issues"] == 0

    @pytest.mark.asyncio
    async def test_llm_response_parsing(self, bug_agent):
        """Test parsing of LLM response"""
        llm_response = """
ISSUE: logic - critical
LINE: 42
DESCRIPTION: Null pointer dereference possible
FIX: Add null check before dereferencing
---
ISSUE: maintainability - low
LINE: multiple
DESCRIPTION: Complex function needs refactoring
FIX: Split into smaller functions
---
"""

        issues = bug_agent._parse_llm_response(llm_response)

        assert len(issues) == 2
        assert issues[0]["category"] == "logic"
        assert issues[0]["severity"] == "critical"
        assert issues[0]["line"] == 42
        assert "Null pointer" in issues[0]["message"]
        assert issues[1]["line"] == 0  # "multiple" should convert to 0

    @pytest.mark.asyncio
    async def test_llm_response_empty(self, bug_agent):
        """Test parsing empty LLM response"""
        issues = bug_agent._parse_llm_response("")

        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_llm_response_malformed(self, bug_agent):
        """Test parsing malformed LLM response"""
        llm_response = "Some random text without proper format"

        issues = bug_agent._parse_llm_response(llm_response)

        # Should handle gracefully, might return empty or partial
        assert isinstance(issues, list)


# ============================================================================
# Test Issue Merging and Sorting
# ============================================================================


class TestIssueMerging:
    """Test issue merging and deduplication"""

    def test_merge_issues_sorts_by_severity(self, bug_agent):
        """Test issues are sorted by severity"""
        static_issues = [
            {"severity": Severity.LOW, "message": "Low issue"},
            {"severity": Severity.CRITICAL, "message": "Critical issue"},
        ]
        llm_issues = [
            {"severity": "high", "message": "High issue"},
            {"severity": "medium", "message": "Medium issue"},
        ]

        merged = bug_agent._merge_issues(static_issues, llm_issues)

        # Should be sorted: CRITICAL, HIGH, MEDIUM, LOW
        severities = [issue["severity"] for issue in merged]
        assert severities[0] == Severity.CRITICAL
        assert severities[-1] == Severity.LOW

    def test_merge_issues_normalizes_severity(self, bug_agent):
        """Test severity normalization during merge"""
        issues = [
            {"severity": "high", "message": "Issue"},
            {"severity": "invalid", "message": "Bad"},
        ]

        merged = bug_agent._merge_issues(issues, [])

        assert all(isinstance(issue["severity"], Severity) for issue in merged)


# ============================================================================
# Test Fix Generation
# ============================================================================


class TestFixGeneration:
    """Test fix suggestion generation"""

    @pytest.mark.asyncio
    async def test_generate_fixes_with_existing_fix(self, bug_agent, python_context):
        """Test fix generation when issue already has fix"""
        issues = [
            {
                "message": "SQL injection",
                "severity": Severity.HIGH,
                "fix": "Use parameterized query",
                "line": 5,
                "pattern": "sql_injection",
                "category": BugCategory.SECURITY,
            }
        ]

        suggestions = await bug_agent._generate_fixes(issues, python_context)

        assert len(suggestions) == 1
        assert suggestions[0].code == "Use parameterized query"
        assert "SQL injection" in suggestions[0].description

    @pytest.mark.asyncio
    async def test_generate_fixes_with_llm(self, bug_agent, python_context):
        """Test fix generation using LLM"""
        bug_agent.llm_manager.generate.return_value = (
            "# Fixed code\nresult = safe_query(params)"
        )

        issues = [
            {
                "message": "Security issue",
                "severity": Severity.HIGH,
                "line": 5,
                "pattern": "custom",
                "category": BugCategory.SECURITY,
            }
        ]

        suggestions = await bug_agent._generate_fixes(issues, python_context)

        assert len(suggestions) == 1
        assert "safe_query" in suggestions[0].code

    @pytest.mark.asyncio
    async def test_generate_fixes_limits_to_ten(self, bug_agent, python_context):
        """Test fix generation limits to top 10 issues"""
        issues = [
            {
                "message": f"Issue {i}",
                "severity": Severity.MEDIUM,
                "fix": f"Fix {i}",
                "line": i,
                "pattern": f"pattern_{i}",
                "category": BugCategory.LOGIC,
            }
            for i in range(20)
        ]

        suggestions = await bug_agent._generate_fixes(issues, python_context)

        assert len(suggestions) == 10

    @pytest.mark.asyncio
    async def test_generate_fix_code_failure(self, bug_agent, python_context):
        """Test fix code generation handles failures"""
        bug_agent.llm_manager.generate.side_effect = Exception("LLM error")

        issue = {
            "message": "Some issue",
            "severity": Severity.MEDIUM,
            "category": BugCategory.LOGIC,
        }

        fix_code = await bug_agent._generate_fix_code(issue, python_context)

        assert "TODO" in fix_code
        assert "Some issue" in fix_code


# ============================================================================
# Test Helper Methods
# ============================================================================


class TestHelperMethods:
    """Test utility and helper methods"""

    def test_get_severity_mapping(self, bug_agent):
        """Test severity mapping for patterns"""
        assert bug_agent._get_severity("sql_injection") == Severity.CRITICAL
        assert bug_agent._get_severity("command_injection") == Severity.CRITICAL
        assert bug_agent._get_severity("hardcoded_secret") == Severity.HIGH
        assert bug_agent._get_severity("nested_loops") == Severity.MEDIUM
        assert bug_agent._get_severity("global_variable") == Severity.LOW
        assert bug_agent._get_severity("unknown_pattern") == Severity.INFO

    def test_get_message_for_patterns(self, bug_agent):
        """Test message generation for patterns"""
        msg = bug_agent._get_message("sql_injection")
        assert "SQL injection" in msg

        msg = bug_agent._get_message("xss_vulnerability")
        assert "XSS" in msg

        msg = bug_agent._get_message("unknown_pattern")
        assert "unknown_pattern" in msg

    def test_get_fix_confidence(self, bug_agent):
        """Test fix confidence calculation"""
        # Static pattern should get higher confidence
        issue_static = {"type": "security", "pattern": "sql_injection"}
        conf = bug_agent._get_fix_confidence(issue_static)
        assert conf in [ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM]

        # LLM detected might be lower
        issue_llm = {"type": "llm_detected", "pattern": "custom"}
        conf = bug_agent._get_fix_confidence(issue_llm)
        assert conf in [
            ConfidenceLevel.HIGH,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.LOW,
        ]

    def test_calculate_confidence_no_issues(self, bug_agent):
        """Test confidence when no issues found"""
        confidence = bug_agent._calculate_confidence([], [])

        assert confidence == 0.9

    def test_calculate_confidence_with_suggestions(self, bug_agent):
        """Test confidence calculation with suggestions"""
        from src.models import Suggestion

        suggestions = [
            Suggestion(
                id="s1",
                code="fix1",
                description="Fix 1",
                confidence=ConfidenceLevel.HIGH,
                diff=None,
                applicable_range=None,
            ),
            Suggestion(
                id="s2",
                code="fix2",
                description="Fix 2",
                confidence=ConfidenceLevel.MEDIUM,
                diff=None,
                applicable_range=None,
            ),
        ]
        issues = [{"message": "issue1"}, {"message": "issue2"}]

        confidence = bug_agent._calculate_confidence(issues, suggestions)

        # Should be average of HIGH (0.95) and MEDIUM (0.75) = 0.85
        assert 0.8 <= confidence <= 0.9

    def test_generate_reasoning_no_issues(self, bug_agent):
        """Test reasoning generation with no issues"""
        reasoning = bug_agent._generate_reasoning([])

        assert "No significant bugs" in reasoning
        assert "clean" in reasoning.lower()

    def test_generate_reasoning_with_issues(self, bug_agent):
        """Test reasoning generation with issues"""
        issues = [
            {"severity": Severity.CRITICAL, "message": "Critical bug"},
            {"severity": Severity.HIGH, "message": "High severity bug"},
            {"severity": Severity.MEDIUM, "message": "Medium bug"},
            {"severity": Severity.LOW, "message": "Low bug"},
            {"severity": Severity.LOW, "message": "Another low bug"},
        ]

        reasoning = bug_agent._generate_reasoning(issues)

        assert "5 issue(s)" in reasoning
        assert "CRITICAL: 1" in reasoning
        assert "HIGH: 1" in reasoning
        assert "Top issues:" in reasoning
        assert "Critical bug" in reasoning

    def test_build_suggestion_id(self, bug_agent):
        """Test suggestion ID generation"""
        issue = {"pattern": "sql_injection"}

        suggestion_id = bug_agent._build_suggestion_id(issue)

        assert suggestion_id.startswith("bug_sql_injection_")
        assert len(suggestion_id) > len("bug_sql_injection_")

    def test_build_description(self, bug_agent):
        """Test description building"""
        issue = {"severity": Severity.HIGH, "message": "Security vulnerability"}

        description = bug_agent._build_description(issue)

        assert "[HIGH]" in description
        assert "Security vulnerability" in description

    def test_build_applicable_range_with_line(self, bug_agent):
        """Test applicable range with line number"""
        issue = {"line": 42}

        range_dict = bug_agent._build_applicable_range(issue)

        assert range_dict is not None
        assert range_dict["start"]["line"] == 42
        assert range_dict["end"]["line"] == 42

    def test_build_applicable_range_without_line(self, bug_agent):
        """Test applicable range without line number"""
        issue = {"line": 0}

        range_dict = bug_agent._build_applicable_range(issue)

        assert range_dict is None

    def test_float_to_confidence(self, bug_agent):
        """Test float to confidence level conversion"""
        assert bug_agent._float_to_confidence(0.95) == ConfidenceLevel.HIGH
        assert bug_agent._float_to_confidence(0.85) == ConfidenceLevel.HIGH
        assert bug_agent._float_to_confidence(0.75) == ConfidenceLevel.MEDIUM
        assert bug_agent._float_to_confidence(0.60) == ConfidenceLevel.MEDIUM
        assert bug_agent._float_to_confidence(0.50) == ConfidenceLevel.LOW
        assert bug_agent._float_to_confidence(0.30) == ConfidenceLevel.LOW

    def test_confidence_to_float(self, bug_agent):
        """Test confidence level to float conversion"""
        assert bug_agent._confidence_to_float(ConfidenceLevel.HIGH) == 0.95
        assert bug_agent._confidence_to_float(ConfidenceLevel.MEDIUM) == 0.75
        assert bug_agent._confidence_to_float(ConfidenceLevel.LOW) == 0.45

    def test_normalize_severity_enum(self, bug_agent):
        """Test severity normalization with Severity enum"""
        result = bug_agent._normalize_severity(Severity.HIGH)

        assert result == Severity.HIGH

    def test_normalize_severity_string(self, bug_agent):
        """Test severity normalization with string"""
        assert bug_agent._normalize_severity("critical") == Severity.CRITICAL
        assert bug_agent._normalize_severity("HIGH") == Severity.HIGH
        assert bug_agent._normalize_severity("medium") == Severity.MEDIUM

    def test_normalize_severity_invalid(self, bug_agent):
        """Test severity normalization with invalid value"""
        assert bug_agent._normalize_severity("invalid") == Severity.INFO
        assert bug_agent._normalize_severity(None) == Severity.INFO
        assert bug_agent._normalize_severity(123) == Severity.INFO


# ============================================================================
# Test Error Handling
# ============================================================================


class TestErrorHandling:
    """Test error handling and edge cases"""

    @pytest.mark.asyncio
    async def test_analyze_code_handles_exception(
        self, bug_agent, base_task, python_context
    ):
        """Test analyze_code handles exceptions gracefully"""
        bug_agent.llm_manager.generate.side_effect = Exception("Unexpected error")

        # Patch _static_analysis to raise exception
        async def failing_static(context):
            raise RuntimeError("Static analysis failed")

        bug_agent._static_analysis = failing_static

        response = await bug_agent.analyze_code(base_task, python_context)

        assert response.agent_id == "bug_agent"
        assert response.confidence == 0.0
        assert response.suggestions == []
        assert "error" in response.metadata
        assert "Static analysis failed" in response.metadata["error"]

    @pytest.mark.asyncio
    async def test_empty_code_analysis(self, bug_agent, base_task):
        """Test analysis of empty code"""
        context = CodeContext(
            file_path="empty.py",
            language="python",
            code="",
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        assert response.agent_id == "bug_agent"
        assert response.suggestions == []

    @pytest.mark.asyncio
    async def test_very_large_code_analysis(self, bug_agent, base_task):
        """Test analysis of very large code"""
        large_code = "def func():\n    pass\n" * 1000

        context = CodeContext(
            file_path="large.py",
            language="python",
            code=large_code,
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        assert response.agent_id == "bug_agent"
        # Should complete without errors


# ============================================================================
# Test Integration Scenarios
# ============================================================================


class TestIntegrationScenarios:
    """Test realistic end-to-end scenarios"""

    @pytest.mark.asyncio
    async def test_complete_security_analysis(self, bug_agent, base_task):
        """Test complete security analysis workflow"""
        context = CodeContext(
            file_path="vulnerable.py",
            language="python",
            code="""
import os
import pickle

api_key = "sk-1234567890"

def execute_command(cmd):
    os.system(cmd)
    
def load_data(data):
    return pickle.loads(data)
    
def query_db(user_id):
    query = "SELECT * FROM users WHERE id=%s" % user_id
    cursor.execute(query)
""",
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        # Should detect multiple security issues
        assert response.metadata["static_issues"] >= 3
        assert len(response.suggestions) > 0
        assert response.confidence > 0.5

        # Check for specific vulnerabilities
        descriptions = [s.description.lower() for s in response.suggestions]
        has_command_injection = any("command" in d for d in descriptions)
        has_sql_injection = any("sql" in d or "injection" in d for d in descriptions)
        has_secret = any("secret" in d or "credential" in d for d in descriptions)

        assert has_command_injection or has_sql_injection or has_secret

    @pytest.mark.asyncio
    async def test_clean_code_analysis(self, bug_agent, base_task):
        """Test analysis of clean, secure code"""
        context = CodeContext(
            file_path="clean.py",
            language="python",
            code="""
from typing import List

def add_numbers(a: int, b: int) -> int:
    '''Add two numbers safely'''
    return a + b

def process_items(items: List[str]) -> List[str]:
    '''Process list items'''
    return [item.strip() for item in items if item]
""",
            workspace_path="/workspace",
            cursor_position={"line": 1, "character": 0},
            git_branch="main",
            selected_text=None,
        )

        response = await bug_agent.analyze_code(base_task, context)

        # Clean code should have no or minimal issues
        assert response.metadata["static_issues"] == 0
        assert response.confidence >= 0.85
        assert "No significant bugs" in response.reasoning
