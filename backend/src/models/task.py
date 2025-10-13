"""
Task data models
Project Creator: Herman Swanepoel
"""

from enum import Enum
from typing import Any, Dict
from pydantic import BaseModel, Field
import time


class TaskType(str, Enum):
    """Types of tasks that can be executed by agents"""
    INLINE_SUGGESTION = "inline_suggestion"
    REFACTOR = "refactor"
    TEST_GENERATION = "test_generation"
    BUG_DETECTION = "bug_detection"
    DOCUMENTATION = "documentation"
    SECURITY_ANALYSIS = "security_analysis"


class Priority(int, Enum):
    """Task priority levels"""
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    CRITICAL = 4


class Task(BaseModel):
    """Task model for agent execution"""
    id: str = Field(..., description="Unique task identifier")
    type: TaskType = Field(..., description="Type of task to execute")
    content: str = Field(..., description="Task content or code to process")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    priority: Priority = Field(default=Priority.MEDIUM, description="Task priority")
    timestamp: float = Field(default_factory=time.time, description="Task creation timestamp")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "task-123",
                "type": "inline_suggestion",
                "content": "async function fetchUser",
                "context": {
                    "file_path": "/src/api/users.ts",
                    "language": "typescript",
                    "cursor_position": {"line": 42, "character": 25}
                },
                "priority": 2,
                "timestamp": 1705132800.0
            }
        }
