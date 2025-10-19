"""
Telemetry Metric Models
Project Creator: Herman Swanepoel
"""

from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional

from pydantic import BaseModel, Field


class MetricType(str, Enum):
    """Types of metrics"""

    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"
    TIMER = "timer"
    LATENCY = "latency"
    ERROR = "error"
    ACCURACY = "accuracy"
    CACHE_HIT = "cache_hit"
    USAGE = "usage"


class Metric(BaseModel):
    """Telemetry metric data model"""

    name: str = Field(..., description="Metric name")
    type: MetricType = Field(..., description="Type of metric")
    value: float = Field(..., description="Metric value")
    unit: Optional[str] = Field(None, description="Unit of measurement")
    tags: Dict[str, str] = Field(default_factory=dict, description="Tags for filtering/grouping")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")
    timestamp: datetime = Field(
        default_factory=datetime.utcnow, description="When metric was recorded"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "name": "api_response_time",
                "type": "latency",
                "value": 0.125,
                "unit": "seconds",
                "tags": {"endpoint": "/api/execute", "method": "POST"},
                "metadata": {"status": "success"},
            }
        }


# Legacy model stubs for backward compatibility
ServiceHealth = Dict[str, Any]
HealthStatus = str
CachePrediction = Dict[str, Any]
CodeContext = Dict[str, Any]
GitCommit = Dict[str, Any]
