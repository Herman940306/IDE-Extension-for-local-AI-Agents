"""
Documentation Agent for generating code documentation
Project Creator: Herman Swanepoel
"""

import logging
import asyncio
from typing import List, Dict, Any, Optional
import re

from models import Task, AgentResponse, Suggestion, TaskType
from adapters.base_adapter import AgentAdapter
from services.llm_manager import LLMManager

logger = logging.getLogger(__name__)


class DocAgent(AgentAdapter):
    """
    Specialized agent for documentation generation
    """
    
    def __init__(self, llm_manager: LLMManager):
        """
        Initialize Doc Agent
        
        Args:
            llm_manager: LLM manager instance
        """
        super().__init__(
            name="doc_agent",
            capabilities=["documentation", "docstrings", "comments", "readme"]
        )
        self.llm_manager = llm_manager
        
        logger.info("✓ DocAgent initialized")
    
    async def execute_task(self, task: Task) -> AgentResponse:
        """
        Execute documentation generation task
        
        Args:
            task: Task to execute
            
        Returns:
            AgentResponse with documentation suggestions
        """
        try:
            logger.info(f"DocAgent executing task: {task.id}")
            
            # Get code context
            code = task.code_context.get("code", "") if task.code_context else ""
            language = task.code_context.get("language", "unknown") if task.code_context else "unknown"
            
            if not code:
                return self._create_empty_response(task)
            
            # Determine documentation type needed
            doc_type = self._determine_doc_type(code, language)
            
            # Generate documentation
            suggestions = await self._generate_documentation(code, language, doc_type)
            
            # Create response
            return AgentResponse(
                task_id=task.id,
                agent_name=self.name,
                suggestions=suggestions,
                metadata={
                    "doc_type": doc_type,
                    "language": language,
                    "suggestions_count": len(suggestions)
                }
            )
            
        except Exception as e:
            logger.error(f"DocAgent task execution failed: {e}")
            return self._create_error_response(task, str(e))
    
    def _determine_doc_type(self, code: str, language: str) -> str:
        """
        Determine what type of documentation is needed
        
        Args:
            code: Code to analyze
            language: Programming language
            
        Returns:
            Documentation type
        """
        # Check for function/method
        if language == "python":
            if re.search(r"^\s*def\s+\w+", code, re.MULTILINE):
                return "function_docstring"
            elif re.search(r"^\s*class\s+\w+", code, re.MULTILINE):
                return "class_docstring"
        elif language in ["javascript", "typescript"]:
            if re.search(r"function\s+\w+|const\s+\w+\s*=\s*\(.*\)\s*=>", code):
                return "jsdoc"
            elif re.search(r"class\s+\w+", code):
                return "class_jsdoc"
        
        return "inline_comments"
    
    async def _generate_documentation(
        self,
        code: str,
        language: str,
        doc_type: str
    ) -> List[Suggestion]:
        """
        Generate documentation suggestions
        
        Args:
            code: Code to document
            language: Programming language
            doc_type: Type of documentation
            
        Returns:
            List of suggestions
        """
        suggestions = []
        
        if doc_type == "function_docstring":
            suggestion = await self._generate_python_docstring(code, "function")
            if suggestion:
                suggestions.append(suggestion)
        
        elif doc_type == "class_docstring":
            suggestion = await self._generate_python_docstring(code, "class")
            if suggestion:
                suggestions.append(suggestion)
        
        elif doc_type == "jsdoc":
            suggestion = await self._generate_jsdoc(code, "function")
            if suggestion:
                suggestions.append(suggestion)
        
        elif doc_type == "class_jsdoc":
            suggestion = await self._generate_jsdoc(code, "class")
            if suggestion:
                suggestions.append(suggestion)
        
        else:
            suggestion = await self._generate_inline_comments(code, language)
            if suggestion:
                suggestions.append(suggestion)
        
        return suggestions
    
    async def _generate_python_docstring(
        self,
        code: str,
        element_type: str
    ) -> Optional[Suggestion]:
        """
        Generate Python docstring
        
        Args:
            code: Python code
            element_type: 'function' or 'class'
            
        Returns:
            Suggestion or None
        """
        try:
            prompt = f"""Generate a comprehensive Python docstring for this {element_type}:

```python
{code}
```

Use Google-style docstring format with:
- Brief description
- Args section (if applicable)
- Returns section (if applicable)
- Raises section (if applicable)
- Example usage (if helpful)

Return the complete code with the docstring added. Only return code, no explanations."""

            documented_code = await self.llm_manager.generate(prompt)
            
            return Suggestion(
                code=documented_code.strip(),
                description=f"Add comprehensive {element_type} docstring",
                confidence=0.9,
                reasoning=f"Generated Google-style Python docstring for {element_type}"
            )
            
        except Exception as e:
            logger.error(f"Failed to generate Python docstring: {e}")
            return None
    
    async def _generate_jsdoc(
        self,
        code: str,
        element_type: str
    ) -> Optional[Suggestion]:
        """
        Generate JSDoc documentation
        
        Args:
            code: JavaScript/TypeScript code
            element_type: 'function' or 'class'
            
        Returns:
            Suggestion or None
        """
        try:
            prompt = f"""Generate comprehensive JSDoc documentation for this {element_type}:

```javascript
{code}
```

Include:
- Description
- @param tags for parameters
- @returns tag
- @throws tag (if applicable)
- @example (if helpful)

Return the complete code with JSDoc added. Only return code, no explanations."""

            documented_code = await self.llm_manager.generate(prompt)
            
            return Suggestion(
                code=documented_code.strip(),
                description=f"Add JSDoc documentation for {element_type}",
                confidence=0.9,
                reasoning=f"Generated comprehensive JSDoc for {element_type}"
            )
            
        except Exception as e:
            logger.error(f"Failed to generate JSDoc: {e}")
            return None
    
    async def _generate_inline_comments(
        self,
        code: str,
        language: str
    ) -> Optional[Suggestion]:
        """
        Generate inline comments for code
        
        Args:
            code: Code to comment
            language: Programming language
            
        Returns:
            Suggestion or None
        """
        try:
            prompt = f"""Add helpful inline comments to this {language} code:

```{language}
{code}
```

Add comments that:
- Explain complex logic
- Clarify intent
- Document edge cases
- Are concise and helpful

Return the complete code with comments added. Only return code, no explanations."""

            commented_code = await self.llm_manager.generate(prompt)
            
            return Suggestion(
                code=commented_code.strip(),
                description="Add inline comments for clarity",
                confidence=0.8,
                reasoning="Generated helpful inline comments explaining code logic"
            )
            
        except Exception as e:
            logger.error(f"Failed to generate inline comments: {e}")
            return None
    
    def _create_empty_response(self, task: Task) -> AgentResponse:
        """Create empty response when no code provided"""
        return AgentResponse(
            task_id=task.id,
            agent_name=self.name,
            suggestions=[],
            metadata={"error": "No code provided for documentation"}
        )
    
    def _create_error_response(self, task: Task, error: str) -> AgentResponse:
        """Create error response"""
        return AgentResponse(
            task_id=task.id,
            agent_name=self.name,
            suggestions=[],
            metadata={"error": error}
        )
    
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return self.capabilities
    
    async def health_check(self) -> bool:
        """Check if agent is healthy"""
        try:
            await self.llm_manager.generate("test", max_tokens=10)
            return True
        except:
            return False
