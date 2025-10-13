"""
Agent response data models
Project Creator: Herman Swanepoel
"""

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class ConfidenceLevel(str, Enum):
    """Confidence levels for suggestions"""
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class Suggestion(BaseModel):
    """Individual suggestion from an agent"""
    id: str = Field(..., description="Unique suggestion identifier")
    code: str = Field(..., description="Suggested code")
    description: str = Field(..., description="Description of the suggestion")
    confidence: ConfidenceLevel = Field(..., description="Confidence level")
    diff: Optional[str] = Field(None, description="Diff representation")
    applicable_range: Optional[Dict[str, Any]] = Field(None, description="Range where suggestion applies")

    class Config:
        json_schema_extra = {
            "example": {
                "id": "sugg-1",
                "code": "async function fetchUser(id: string): Promise<User>",
                "description": "Added type annotations for better type safety",
                "confidence": "high",
                "diff": None,
                "applicable_range": None
            }
        }


class AgentResponse(BaseModel):
    """Response from an agent"""
    agent_id: str = Field(..., description="Agent identifier")
    agent_name: str = Field(..., description="Human-readable agent name")
    suggestions: List[Suggestion] = Field(default_factory=list, description="List of suggestions")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence score")
    reasoning: str = Field(..., description="Explanation of the reasoning")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional metadata")

    class Config:
        json_schema_extra = {
            "example": {
                "agent_id": "refactor_agent",
                "agent_name": "Refactor Agent",
                "suggestions": [
                    {
                        "id": "sugg-1",
                        "code": "async function fetchUser(id: string): Promise<User>",
                        "description": "Added type annotations",
                        "confidence": "high"
                    }
                ],
                "confidence": 0.92,
                "reasoning": "TypeScript best practices recommend explicit return types",
                "metadata": {}
            }
        }
