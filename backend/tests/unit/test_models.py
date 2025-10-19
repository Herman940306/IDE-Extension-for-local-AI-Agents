"""
Unit tests for Data Models

Project Creator: Herman Swanepoel
Date: 2025-10-13
Target Coverage: 95%
GODMODE: AUTONOMOUS EXECUTION
"""

import pytest
import time
from pydantic import ValidationError
from src.models.code_smell import CodeSmell
from src.models.context import CodeContext, GitCommit
from src.models.response import AgentResponse, Suggestion, ConfidenceLevel
from src.models.task import Task, TaskType, Priority


# ============================================================================
# CodeSmell Model Tests
# ============================================================================


class TestCodeSmellModel:
    """Test CodeSmell data model"""

    def test_code_smell_creation_valid(self):
        """Test creating a valid code smell"""
        smell = CodeSmell(
            id="smell-1",
            file_path="test.py",
            smell_type="god_class",
            severity=Priority.HIGH,
            description="Too many methods",
            line_start=10,
            line_end=100,
            suggestion="Split into smaller classes",
            confidence=0.9,
        )

        assert smell.id == "smell-1"
        assert smell.file_path == "test.py"
        assert smell.smell_type == "god_class"
        assert smell.severity == Priority.HIGH
        assert smell.confidence == 0.9

    def test_code_smell_confidence_validation(self):
        """Test confidence score validation (0.0 to 1.0)"""
        # Valid confidence
        smell = CodeSmell(
            id="smell-1",
            file_path="test.py",
            smell_type="long_function",
            severity=Priority.MEDIUM,
            description="Function too long",
            line_start=1,
            line_end=50,
            suggestion="Break into smaller functions",
            confidence=0.5,
        )
        assert smell.confidence == 0.5

        # Invalid confidence > 1.0
        with pytest.raises(ValidationError):
            CodeSmell(
                id="smell-2",
                file_path="test.py",
                smell_type="long_function",
                severity=Priority.MEDIUM,
                description="Test",
                line_start=1,
                line_end=50,
                suggestion="Test",
                confidence=1.5,
            )

        # Invalid confidence < 0.0
        with pytest.raises(ValidationError):
            CodeSmell(
                id="smell-3",
                file_path="test.py",
                smell_type="long_function",
                severity=Priority.MEDIUM,
                description="Test",
                line_start=1,
                line_end=50,
                suggestion="Test",
                confidence=-0.1,
            )

    def test_code_smell_required_fields(self):
        """Test that all required fields must be provided"""
        with pytest.raises(ValidationError):
            CodeSmell(
                id="smell-1",
                file_path="test.py",
                # Missing required fields
            )

    def test_code_smell_serialization(self):
        """Test code smell serialization to dict"""
        smell = CodeSmell(
            id="smell-1",
            file_path="test.py",
            smell_type="duplicate_code",
            severity=Priority.LOW,
            description="Duplicate code detected",
            line_start=10,
            line_end=20,
            suggestion="Extract to function",
            confidence=0.8,
        )

        data = smell.model_dump()

        assert data["id"] == "smell-1"
        assert data["smell_type"] == "duplicate_code"
        assert data["confidence"] == 0.8

    def test_code_smell_from_dict(self):
        """Test creating code smell from dictionary"""
        data = {
            "id": "smell-1",
            "file_path": "test.py",
            "smell_type": "complex_method",
            "severity": Priority.HIGH,
            "description": "High complexity",
            "line_start": 1,
            "line_end": 100,
            "suggestion": "Simplify logic",
            "confidence": 0.95,
        }

        smell = CodeSmell(**data)

        assert smell.id == "smell-1"
        assert smell.confidence == 0.95


# ============================================================================
# Context Model Tests
# ============================================================================


class TestGitCommitModel:
    """Test GitCommit data model"""

    def test_git_commit_creation(self):
        """Test creating a git commit"""
        commit = GitCommit(
            hash="abc123", message="Fix bug", author="John Doe", timestamp=1705132800.0
        )

        assert commit.hash == "abc123"
        assert commit.message == "Fix bug"
        assert commit.author == "John Doe"
        assert commit.timestamp == 1705132800.0

    def test_git_commit_required_fields(self):
        """Test that all fields are required"""
        with pytest.raises(ValidationError):
            GitCommit(
                hash="abc123",
                message="Fix bug",
                # Missing author and timestamp
            )


class TestCodeContextModel:
    """Test CodeContext data model"""

    def test_code_context_minimal(self):
        """Test creating code context with minimal fields"""
        context = CodeContext(file_path="test.py", language="python")

        assert context.file_path == "test.py"
        assert context.language == "python"
        assert context.workspace_path is None
        assert context.imports == []
        assert context.dependencies == []

    def test_code_context_full(self):
        """Test creating code context with all fields"""
        commits = [
            GitCommit(
                hash="abc123",
                message="Initial commit",
                author="John Doe",
                timestamp=1705132800.0,
            )
        ]

        context = CodeContext(
            file_path="test.py",
            language="python",
            workspace_path="/workspace",
            cursor_position={"line": 10, "character": 5},
            selected_text="def test():",
            surrounding_code="class TestClass:",
            imports=["import os", "import sys"],
            dependencies=["module1", "module2"],
            git_branch="main",
            recent_commits=commits,
        )

        assert context.file_path == "test.py"
        assert context.cursor_position == {"line": 10, "character": 5}
        assert len(context.imports) == 2
        assert len(context.recent_commits) == 1

    def test_code_context_default_values(self):
        """Test default values for optional fields"""
        context = CodeContext(file_path="test.py", language="python")

        assert context.surrounding_code == ""
        assert context.imports == []
        assert context.dependencies == []
        assert context.recent_commits == []

    def test_code_context_serialization(self):
        """Test code context serialization"""
        context = CodeContext(file_path="test.py", language="python", imports=["import os"])

        data = context.model_dump()

        assert data["file_path"] == "test.py"
        assert data["language"] == "python"
        assert data["imports"] == ["import os"]


# ============================================================================
# Response Model Tests
# ============================================================================


class TestConfidenceLevelEnum:
    """Test ConfidenceLevel enum"""

    def test_confidence_levels(self):
        """Test all confidence level values"""
        assert ConfidenceLevel.HIGH == "high"
        assert ConfidenceLevel.MEDIUM == "medium"
        assert ConfidenceLevel.LOW == "low"

    def test_confidence_level_comparison(self):
        """Test confidence level string comparison"""
        assert ConfidenceLevel.HIGH.value == "high"
        assert ConfidenceLevel.MEDIUM.value == "medium"


class TestSuggestionModel:
    """Test Suggestion data model"""

    def test_suggestion_creation_minimal(self):
        """Test creating suggestion with minimal fields"""
        suggestion = Suggestion(
            id="sugg-1",
            code="def test(): pass",
            description="Test function",
            confidence=ConfidenceLevel.HIGH,
        )

        assert suggestion.id == "sugg-1"
        assert suggestion.code == "def test(): pass"
        assert suggestion.confidence == ConfidenceLevel.HIGH
        assert suggestion.diff is None

    def test_suggestion_creation_full(self):
        """Test creating suggestion with all fields"""
        suggestion = Suggestion(
            id="sugg-1",
            code="def test(): pass",
            description="Test function",
            confidence=ConfidenceLevel.MEDIUM,
            diff="+def test(): pass",
            applicable_range={"start": 10, "end": 20},
        )

        assert suggestion.diff == "+def test(): pass"
        assert suggestion.applicable_range == {"start": 10, "end": 20}

    def test_suggestion_confidence_enum(self):
        """Test suggestion with different confidence levels"""
        for level in [
            ConfidenceLevel.HIGH,
            ConfidenceLevel.MEDIUM,
            ConfidenceLevel.LOW,
        ]:
            suggestion = Suggestion(id="sugg-1", code="test", description="test", confidence=level)
            assert suggestion.confidence == level


class TestAgentResponseModel:
    """Test AgentResponse data model"""

    def test_agent_response_minimal(self):
        """Test creating agent response with minimal fields"""
        response = AgentResponse(
            agent_id="agent-1",
            agent_name="Test Agent",
            confidence=0.9,
            reasoning="Test reasoning",
        )

        assert response.agent_id == "agent-1"
        assert response.agent_name == "Test Agent"
        assert response.confidence == 0.9
        assert response.suggestions == []
        assert response.metadata == {}

    def test_agent_response_with_suggestions(self):
        """Test agent response with suggestions"""
        suggestions = [
            Suggestion(
                id="sugg-1",
                code="def test1(): pass",
                description="Test 1",
                confidence=ConfidenceLevel.HIGH,
            ),
            Suggestion(
                id="sugg-2",
                code="def test2(): pass",
                description="Test 2",
                confidence=ConfidenceLevel.MEDIUM,
            ),
        ]

        response = AgentResponse(
            agent_id="agent-1",
            agent_name="Test Agent",
            suggestions=suggestions,
            confidence=0.85,
            reasoning="Multiple suggestions",
            metadata={"version": "1.0"},
        )

        assert len(response.suggestions) == 2
        assert response.suggestions[0].id == "sugg-1"
        assert response.metadata["version"] == "1.0"

    def test_agent_response_confidence_validation(self):
        """Test confidence score validation"""
        # Valid confidence
        response = AgentResponse(
            agent_id="agent-1",
            agent_name="Test Agent",
            confidence=0.5,
            reasoning="Test",
        )
        assert response.confidence == 0.5

        # Invalid confidence
        with pytest.raises(ValidationError):
            AgentResponse(
                agent_id="agent-1",
                agent_name="Test Agent",
                confidence=1.5,
                reasoning="Test",
            )


# ============================================================================
# Task Model Tests
# ============================================================================


class TestTaskTypeEnum:
    """Test TaskType enum"""

    def test_task_types(self):
        """Test all task type values"""
        assert TaskType.INLINE_SUGGESTION == "inline_suggestion"
        assert TaskType.REFACTOR == "refactor"
        assert TaskType.TEST_GENERATION == "test_generation"
        assert TaskType.BUG_DETECTION == "bug_detection"
        assert TaskType.DOCUMENTATION == "documentation"
        assert TaskType.SECURITY_ANALYSIS == "security_analysis"


class TestPriorityEnum:
    """Test Priority enum"""

    def test_priority_levels(self):
        """Test all priority level values"""
        assert Priority.LOW == 1
        assert Priority.MEDIUM == 2
        assert Priority.HIGH == 3
        assert Priority.CRITICAL == 4

    def test_priority_comparison(self):
        """Test priority level comparison"""
        assert Priority.CRITICAL > Priority.HIGH
        assert Priority.HIGH > Priority.MEDIUM
        assert Priority.MEDIUM > Priority.LOW


class TestTaskModel:
    """Test Task data model"""

    def test_task_creation_minimal(self):
        """Test creating task with minimal fields"""
        task = Task(id="task-1", type=TaskType.REFACTOR, content="def test(): pass")

        assert task.id == "task-1"
        assert task.type == TaskType.REFACTOR
        assert task.content == "def test(): pass"
        assert task.priority == Priority.MEDIUM  # Default
        assert task.context == {}

    def test_task_creation_full(self):
        """Test creating task with all fields"""
        context = {"file_path": "test.py", "language": "python"}

        task = Task(
            id="task-1",
            type=TaskType.BUG_DETECTION,
            content="def buggy_function(): pass",
            context=context,
            priority=Priority.HIGH,
            timestamp=1705132800.0,
        )

        assert task.context == context
        assert task.priority == Priority.HIGH
        assert task.timestamp == 1705132800.0

    def test_task_default_timestamp(self):
        """Test that timestamp is auto-generated"""
        before = time.time()

        task = Task(id="task-1", type=TaskType.INLINE_SUGGESTION, content="test")

        after = time.time()

        assert before <= task.timestamp <= after

    def test_task_all_types(self):
        """Test creating tasks with all task types"""
        for task_type in TaskType:
            task = Task(id=f"task-{task_type.value}", type=task_type, content="test content")
            assert task.type == task_type

    def test_task_all_priorities(self):
        """Test creating tasks with all priority levels"""
        for priority in Priority:
            task = Task(
                id=f"task-{priority.value}",
                type=TaskType.REFACTOR,
                content="test content",
                priority=priority,
            )
            assert task.priority == priority

    def test_task_serialization(self):
        """Test task serialization to dict"""
        task = Task(
            id="task-1",
            type=TaskType.DOCUMENTATION,
            content="Add docstrings",
            priority=Priority.LOW,
        )

        data = task.model_dump()

        assert data["id"] == "task-1"
        assert data["type"] == "documentation"
        assert data["priority"] == 1

    def test_task_from_dict(self):
        """Test creating task from dictionary"""
        data = {
            "id": "task-1",
            "type": "security_analysis",
            "content": "Check for vulnerabilities",
            "context": {"file": "app.py"},
            "priority": 4,
            "timestamp": 1705132800.0,
        }

        task = Task(**data)

        assert task.id == "task-1"
        assert task.type == TaskType.SECURITY_ANALYSIS
        assert task.priority == Priority.CRITICAL


# ============================================================================
# Integration Tests
# ============================================================================


class TestModelIntegration:
    """Test model integration scenarios"""

    def test_agent_response_with_code_smell(self):
        """Test agent response containing code smell suggestions"""
        smell = CodeSmell(
            id="smell-1",
            file_path="test.py",
            smell_type="god_class",
            severity=Priority.HIGH,
            description="Too many methods",
            line_start=1,
            line_end=100,
            suggestion="Split class",
            confidence=0.9,
        )

        suggestion = Suggestion(
            id="sugg-1",
            code="# Refactored code",
            description=smell.suggestion,
            confidence=ConfidenceLevel.HIGH,
        )

        response = AgentResponse(
            agent_id="refactor_agent",
            agent_name="Refactor Agent",
            suggestions=[suggestion],
            confidence=smell.confidence,
            reasoning=smell.description,
        )

        assert response.confidence == smell.confidence
        assert response.suggestions[0].description == smell.suggestion

    def test_task_with_code_context(self):
        """Test task containing code context"""
        context_obj = CodeContext(
            file_path="test.py",
            language="python",
            cursor_position={"line": 10, "character": 5},
        )

        task = Task(
            id="task-1",
            type=TaskType.INLINE_SUGGESTION,
            content="def test(): pass",
            context=context_obj.model_dump(),
            priority=Priority.MEDIUM,
        )

        assert task.context["file_path"] == "test.py"
        assert task.context["language"] == "python"

    def test_complete_workflow_models(self):
        """Test complete workflow using all models"""
        # 1. Create task
        task = Task(
            id="task-1",
            type=TaskType.REFACTOR,
            content="class GodClass: pass",
            priority=Priority.HIGH,
        )

        # 2. Create context
        context = CodeContext(file_path="god_class.py", language="python")

        # 3. Detect code smell
        smell = CodeSmell(
            id="smell-1",
            file_path=context.file_path,
            smell_type="god_class",
            severity=Priority.HIGH,
            description="Too many responsibilities",
            line_start=1,
            line_end=100,
            suggestion="Apply Single Responsibility Principle",
            confidence=0.95,
        )

        # 4. Create suggestion
        suggestion = Suggestion(
            id="sugg-1",
            code="# Refactored code here",
            description=smell.suggestion,
            confidence=ConfidenceLevel.HIGH,
        )

        # 5. Create agent response
        response = AgentResponse(
            agent_id="refactor_agent",
            agent_name="Refactor Agent",
            suggestions=[suggestion],
            confidence=smell.confidence,
            reasoning=smell.description,
        )

        # Verify workflow
        assert task.type == TaskType.REFACTOR
        assert smell.file_path == context.file_path
        assert response.suggestions[0].description == smell.suggestion
        assert response.confidence == smell.confidence
