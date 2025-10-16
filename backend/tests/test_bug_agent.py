"""Unit tests for BugAgent"""

from unittest.mock import AsyncMock, Mock

import pytest
from src.agents.bug_agent import BugAgent
from src.models import CodeContext, ConfidenceLevel, Priority, Task, TaskType
from src.services.llm_manager import LLMManager


@pytest.fixture
def llm_manager():
    manager = Mock(spec=LLMManager)
    manager.generate = AsyncMock(return_value="")
    return manager


@pytest.fixture
def bug_agent(llm_manager):
    return BugAgent(llm_manager)


@pytest.fixture
def base_task():
    return Task(
        id="task-1",
        type=TaskType.BUG_DETECTION,
        content="",
        context={"workspace_path": "/tmp/workspace"},
        priority=Priority.MEDIUM,
        description="Detect bugs",
    )


@pytest.fixture
def safe_context():
    return CodeContext(
        file_path="app.py",
        language="python",
        code="def add(a, b):\n    return a + b",
        workspace_path="/tmp/workspace",
        cursor_position={"line": 1, "character": 0},
        git_branch="main",
        selected_text=None,
    )


@pytest.fixture
def insecure_context():
    return CodeContext(
        file_path="vulnerable.py",
        language="python",
        code="import os\n\ndef run(cmd):\n    os.system(cmd)",
        workspace_path="/tmp/workspace",
        cursor_position={"line": 1, "character": 0},
        git_branch="main",
        selected_text=None,
    )


@pytest.mark.asyncio
async def test_static_security_detection(bug_agent, base_task, insecure_context, llm_manager):
    llm_manager.generate.return_value = "# fix"

    response = await bug_agent.analyze_code(base_task, insecure_context)

    assert response.agent_id == "bug_agent"
    assert response.metadata["static_issues"] >= 1
    assert response.suggestions
    first = response.suggestions[0]
    assert "command injection" in first.description.lower()
    assert first.confidence is ConfidenceLevel.HIGH


@pytest.mark.asyncio
async def test_confidence_when_no_issues(bug_agent, base_task, safe_context):
    response = await bug_agent.analyze_code(base_task, safe_context)

    assert response.suggestions == []
    assert response.confidence >= 0.85
    assert response.reasoning.startswith("No significant bugs")


@pytest.mark.asyncio
async def test_llm_issue_parsing(base_task, safe_context):
    llm_manager = Mock(spec=LLMManager)
    llm_manager.generate = AsyncMock(
        side_effect=[
            "ISSUE: security - high\nLINE: 5\nDESCRIPTION: Vulnerability\nFIX: Use safe API\n---",
            "print('fixed')",
        ]
    )
    agent = BugAgent(llm_manager)

    response = await agent.analyze_code(base_task, safe_context)

    assert response.metadata["llm_issues"] == 1
    assert response.suggestions
    assert response.suggestions[0].code == "Use safe API"
    assert response.suggestions[0].confidence in {ConfidenceLevel.HIGH, ConfidenceLevel.MEDIUM}


@pytest.mark.asyncio
async def test_handles_analysis_failure(bug_agent, base_task, insecure_context, monkeypatch):
    async def failing_static(context):
        raise RuntimeError("failure")

    monkeypatch.setattr(bug_agent, "_static_analysis", failing_static)

    response = await bug_agent.analyze_code(base_task, insecure_context)

    assert response.confidence == 0.0
    assert response.suggestions == []
    assert "failure" in response.metadata["error"]
