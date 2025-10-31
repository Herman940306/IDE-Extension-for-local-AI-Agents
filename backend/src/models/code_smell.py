"""
Code smell data models
Project Creator: Herman Swanepoel
"""

from pydantic import BaseModel, ConfigDict, Field
from src.models.task import Priority


class CodeSmell(BaseModel):
    """Represents a detected code smell"""

    id: str = Field(..., description="Unique identifier for the code smell")
    file_path: str = Field(..., description="Path to the file containing the smell")
    smell_type: str = Field(
        ..., description="Type of code smell (e.g., 'god_class', 'long_function')"
    )
    severity: Priority = Field(..., description="Severity level of the smell")
    description: str = Field(..., description="Description of the code smell")
    line_start: int = Field(..., description="Starting line number")
    line_end: int = Field(..., description="Ending line number")
    suggestion: str = Field(..., description="Suggested fix or refactoring")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score (0.0 to 1.0)")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "god_class_UserManager",
                "file_path": "src/services/user_manager.py",
                "smell_type": "god_class",
                "severity": 3,
                "description": "Class 'UserManager' has 15 methods (threshold: 10)",
                "line_start": 10,
                "line_end": 250,
                "suggestion": "Consider splitting into smaller, focused classes using Single Responsibility Principle",  # noqa: E501
                "confidence": 0.9,
            }
        }
    )
