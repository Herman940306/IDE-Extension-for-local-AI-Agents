"""
Data Models for Enterprise AI Agents Integration

Project Creator: Herman Swanepoel
Version: 1.0
"""

from enum import Enum
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, Field


# ============================================================================
# TASK MODELS
# ============================================================================

class TaskType(str, Enum):
    """Task type classification"""
    CODE_GENERATION = "code_generation"
    CODE_REVIEW = "code_review"
    REFACTORING = "refactoring"
    DEBUGGING = "debugging"
    DOCUMENTATION = "documentation"
    TESTING = "testing"
    ARCHITECTURE = "architecture"
    GENERAL = "general"


class Priority(str, Enum):
    """Task priority levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Task(BaseModel):
    """Task representation"""
    id: str
    type: TaskType
    priority: Priority
    description: str
    context: Optional[str] = None
    file_path: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# AGENT RESPONSE MODELS
# ============================================================================

class Suggestion(BaseModel):
    """Code suggestion from agent"""
    id: str
    content: str
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: Optional[str] = None
    file_path: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    tags: List[str] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.now)


class AgentResponse(BaseModel):
    """Complete agent response"""
    task_id: str
    suggestions: List[Suggestion] = Field(default_factory=list)
    summary: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    processing_time_ms: Optional[float] = None
    model_used: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# CODE CONTEXT MODELS
# ============================================================================

class CodeContext(BaseModel):
    """Code context information"""
    file_path: str
    content: str
    language: str
    imports: List[str] = Field(default_factory=list)
    functions: List[str] = Field(default_factory=list)
    classes: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    line_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)


class CodeEmbedding(BaseModel):
    """Code embedding representation"""
    id: str
    file_path: str
    chunk_index: int
    content: str
    embedding: List[float]
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.now)


# ============================================================================
# GIT MODELS
# ============================================================================

class GitCommit(BaseModel):
    """Git commit information"""
    hash: str
    author: str
    email: str
    message: str
    timestamp: datetime
    files_changed: List[str] = Field(default_factory=list)
    additions: int = 0
    deletions: int = 0


# ============================================================================
# TELEMETRY MODELS (Task 5.4)
# ============================================================================

class MetricType(str, Enum):
    """Metric type classification"""
    LATENCY = "latency"
    ACCURACY = "accuracy"
    CACHE_HIT = "cache_hit"
    ERROR = "error"
    USAGE = "usage"


class Metric(BaseModel):
    """Telemetry metric"""
    name: str
    type: MetricType
    value: float
    unit: str
    timestamp: datetime = Field(default_factory=datetime.now)
    tags: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


# ============================================================================
# INNOVATION FEATURE MODELS (Task 5)
# ============================================================================

class CodeSmell(BaseModel):
    """Code smell detection result"""
    id: str
    file_path: str
    smell_type: str
    severity: Priority
    description: str
    line_start: int
    line_end: int
    suggestion: Optional[str] = None
    confidence: float = Field(ge=0.0, le=1.0)
    detected_at: datetime = Field(default_factory=datetime.now)


class CachePrediction(BaseModel):
    """Predictive cache entry"""
    key: str
    predicted_access_time: datetime
    confidence: float = Field(ge=0.0, le=1.0)
    access_pattern: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthStatus(str, Enum):
    """Service health status"""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class ServiceHealth(BaseModel):
    """Service health check result"""
    service_name: str
    status: HealthStatus
    latency_ms: Optional[float] = None
    error_rate: Optional[float] = None
    last_check: datetime = Field(default_factory=datetime.now)
    details: Dict[str, Any] = Field(default_factory=dict)
