"""
Data models for Enterprise AI Agents Integration
Project Creator: Herman Swanepoel
"""

from .task import Task, TaskType, Priority
from .response import AgentResponse, Suggestion, ConfidenceLevel
from .context import CodeContext, GitCommit
from .code_smell import CodeSmell

__all__ = [
    "Task",
    "TaskType",
    "Priority",
    "AgentResponse",
    "Suggestion",
    "ConfidenceLevel",
    "CodeContext",
    "GitCommit",
    "CodeSmell",
]
