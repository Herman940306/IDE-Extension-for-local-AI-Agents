"""
Task session models and WebSocket payload contracts.
Project Creator: Herman Swanepoel
"""

from __future__ import annotations

import time
from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field, computed_field

from .response import AgentResponse
from .task import Priority, TaskType


class TaskContextPayload(BaseModel):
    """Contextual information supplied with a task request."""

    language: Optional[str] = Field(
        default=None, description="Preferred programming language"
    )
    file_path: Optional[str] = Field(default=None, description="Associated file path")
    repository: Optional[str] = Field(
        default=None, description="Repository or project identifier"
    )
    cursor_position: Optional[Dict[str, int]] = Field(
        default=None, description="Cursor position information from the editor"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional context metadata",
    )


class TaskRequestPayload(BaseModel):
    """Incoming payload from the WebSocket client describing a task to execute."""

    id: str = Field(..., description="Client supplied task identifier")
    type: TaskType = Field(..., description="Type of task to execute")
    description: str = Field(..., description="High level description of the task")
    content: Optional[str] = Field(
        default=None, description="Primary code or text content"
    )
    context: TaskContextPayload = Field(
        default_factory=TaskContextPayload,
        description="Editor context supplied by the client",
    )
    priority: Priority = Field(
        default=Priority.MEDIUM, description="Desired task priority"
    )
    mode: Optional[str] = Field(
        default=None, description="Optional execution mode override"
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict, description="Additional metadata"
    )


class TaskAcceptedPayload(BaseModel):
    """Acknowledgement message sent after a task is accepted for processing."""

    task_id: str = Field(..., description="Identifier of the accepted task")
    status: str = Field(default="accepted", description="Processing status")
    received_at: float = Field(
        default_factory=lambda: time.time(), description="Server timestamp"
    )
    message: str = Field(
        default="Task received and queued for processing",
        description="Human readable acknowledgement message",
    )


class VerificationStatus(str, Enum):
    """Enum describing verification outcome."""

    SKIPPED = "skipped"
    PASSED = "passed"
    FAILED = "failed"


class VerificationSummary(BaseModel):
    """Summary of verification stage for a task."""

    status: VerificationStatus = Field(..., description="Verification outcome")
    confidence: float = Field(
        default=0.0, ge=0.0, le=1.0, description="Verification confidence"
    )
    issues: List[Dict[str, Any]] = Field(
        default_factory=list,
        description="Issues found during verification",
    )
    metadata: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional verification metadata",
    )


class AgentRunResult(BaseModel):
    """Metadata captured for an individual agent invocation."""

    response: AgentResponse = Field(..., description="Agent response payload")
    duration_ms: float = Field(
        ..., ge=0.0, description="Processing latency in milliseconds"
    )
    escalated: bool = Field(
        default=False,
        description="Whether the request escalated to verification",
    )


class TaskSessionResult(BaseModel):
    """Aggregate result returned to WebSocket clients after processing a task."""

    task_id: str = Field(..., description="Identifier of the processed task")
    status: str = Field(default="completed", description="Overall processing status")
    summary: str = Field(..., description="Human readable summary of the result")
    responses: List[AgentRunResult] = Field(
        default_factory=list, description="List of individual agent run results"
    )
    verification: Optional[VerificationSummary] = Field(
        default=None, description="Verification summary when applicable"
    )
    metrics: Dict[str, Any] = Field(
        default_factory=dict,
        description="Additional processing metrics",
    )
    errors: List[str] = Field(
        default_factory=list,
        description="Errors encountered during processing",
    )

    @computed_field(return_type=str)  # type: ignore[misc]
    @property
    def reasoning(self) -> str:
        """Compatibility field consumed by the current frontend."""
        return self.summary


__all__ = [
    "AgentRunResult",
    "TaskAcceptedPayload",
    "TaskContextPayload",
    "TaskRequestPayload",
    "TaskSessionResult",
    "VerificationStatus",
    "VerificationSummary",
]
