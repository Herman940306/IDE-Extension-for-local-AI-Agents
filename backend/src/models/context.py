"""
Code context data models
Project Creator: Herman Swanepoel
"""

from typing import List, Optional
from pydantic import BaseModel, Field


class GitCommit(BaseModel):
    """Git commit information"""
    hash: str = Field(..., description="Commit hash")
    message: str = Field(..., description="Commit message")
    author: str = Field(..., description="Commit author")
    timestamp: float = Field(..., description="Commit timestamp")


class CodeContext(BaseModel):
    """Context information for code analysis"""
    file_path: str = Field(..., description="Path to the file")
    language: str = Field(..., description="Programming language")
    cursor_position: Optional[dict] = Field(None, description="Cursor position (line, character)")
    selected_text: Optional[str] = Field(None, description="Currently selected text")
    surrounding_code: str = Field(default="", description="Code surrounding the cursor")
    imports: List[str] = Field(default_factory=list, description="Import statements")
    dependencies: List[str] = Field(default_factory=list, description="File dependencies")
    git_branch: Optional[str] = Field(None, description="Current Git branch")
    recent_commits: List[GitCommit] = Field(default_factory=list, description="Recent commits")

    class Config:
        json_schema_extra = {
            "example": {
                "file_path": "/src/api/users.ts",
                "language": "typescript",
                "cursor_position": {"line": 42, "character": 25},
                "selected_text": None,
                "surrounding_code": "export class UserService {",
                "imports": ["import { User } from './types'"],
                "dependencies": ["./types", "./database"],
                "git_branch": "feature/user-api",
                "recent_commits": []
            }
        }
