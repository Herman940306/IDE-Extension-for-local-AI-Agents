"""
Prompt templates for different agent tasks
Project Creator: Herman Swanepoel
"""

from typing import Dict, Any
from src.models import TaskType


class PromptTemplates:
    """Collection of prompt templates for different tasks"""

    @staticmethod
    def get_system_prompt(task_type: TaskType) -> str:
        """
        Get system prompt for a specific task type
        
        Args:
            task_type: Type of task
            
        Returns:
            System prompt string
        """
        prompts = {
            TaskType.INLINE_SUGGESTION: """You are an expert code completion assistant. 
Your role is to provide intelligent, context-aware code suggestions that help developers write better code faster.
Focus on:
- Type safety and best practices
- Idiomatic code patterns
- Performance considerations
- Clear and maintainable code

Provide concise, accurate suggestions with brief explanations.""",

            TaskType.REFACTOR: """You are an expert code refactoring assistant.
Your role is to analyze code and suggest improvements for:
- Code quality and maintainability
- Design patterns and architecture
- Performance optimization
- Reducing complexity and code smells

Provide specific, actionable refactoring suggestions with clear reasoning.""",

            TaskType.TEST_GENERATION: """You are an expert test generation assistant.
Your role is to create comprehensive test cases that:
- Cover core functionality and edge cases
- Follow testing best practices
- Use appropriate testing frameworks
- Include clear test descriptions

Generate well-structured, meaningful tests.""",

            TaskType.BUG_DETECTION: """You are an expert bug detection assistant.
Your role is to identify potential issues including:
- Logic errors and edge cases
- Type mismatches and null pointer issues
- Resource leaks and performance problems
- Security vulnerabilities

Provide clear explanations of issues and suggested fixes.""",

            TaskType.DOCUMENTATION: """You are an expert documentation assistant.
Your role is to create clear, comprehensive documentation including:
- Function/class docstrings
- API documentation
- Code comments for complex logic
- README sections

Write documentation that is clear, concise, and helpful.""",

            TaskType.SECURITY_ANALYSIS: """You are an expert security analysis assistant.
Your role is to identify security vulnerabilities including:
- Injection attacks (SQL, XSS, etc.)
- Authentication and authorization issues
- Data exposure and privacy concerns
- Insecure dependencies

Provide severity ratings and remediation steps."""
        }

        return prompts.get(task_type, "You are a helpful coding assistant.")

    @staticmethod
    def build_code_suggestion_prompt(code: str, context: Dict[str, Any]) -> str:
        """
        Build prompt for inline code suggestions
        
        Args:
            code: Code snippet
            context: Additional context
            
        Returns:
            Formatted prompt
        """
        language = context.get('language', 'unknown')
        file_path = context.get('file_path', '')
        
        return f"""Given the following {language} code:

File: {file_path}
```{language}
{code}
```

Provide intelligent code completion suggestions. Consider:
1. The programming language and its idioms
2. Type safety and best practices
3. The context of the surrounding code
4. Common patterns in this language

Suggest 1-3 completions with confidence levels (high/medium/low) and brief explanations."""

    @staticmethod
    def build_refactor_prompt(code: str, context: Dict[str, Any]) -> str:
        """
        Build prompt for code refactoring
        
        Args:
            code: Code to refactor
            context: Additional context
            
        Returns:
            Formatted prompt
        """
        language = context.get('language', 'unknown')
        
        return f"""Analyze this {language} code and suggest refactoring improvements:

```{language}
{code}
```

Identify:
1. Code smells and anti-patterns
2. Opportunities for simplification
3. Performance improvements
4. Better design patterns

Provide specific refactoring suggestions with before/after examples."""

    @staticmethod
    def build_test_generation_prompt(code: str, context: Dict[str, Any]) -> str:
        """
        Build prompt for test generation
        
        Args:
            code: Code to test
            context: Additional context
            
        Returns:
            Formatted prompt
        """
        language = context.get('language', 'unknown')
        
        return f"""Generate comprehensive tests for this {language} code:

```{language}
{code}
```

Create tests that:
1. Cover main functionality
2. Test edge cases and error conditions
3. Follow testing best practices for {language}
4. Use appropriate testing framework

Provide complete, runnable test code."""

    @staticmethod
    def build_bug_detection_prompt(code: str, context: Dict[str, Any]) -> str:
        """
        Build prompt for bug detection
        
        Args:
            code: Code to analyze
            context: Additional context
            
        Returns:
            Formatted prompt
        """
        language = context.get('language', 'unknown')
        
        return f"""Analyze this {language} code for potential bugs and issues:

```{language}
{code}
```

Look for:
1. Logic errors and edge cases
2. Type safety issues
3. Resource management problems
4. Performance bottlenecks
5. Security vulnerabilities

For each issue found, provide:
- Severity (critical/high/medium/low)
- Description of the problem
- Suggested fix"""

    @staticmethod
    def build_documentation_prompt(code: str, context: Dict[str, Any]) -> str:
        """
        Build prompt for documentation generation
        
        Args:
            code: Code to document
            context: Additional context
            
        Returns:
            Formatted prompt
        """
        language = context.get('language', 'unknown')
        
        return f"""Generate comprehensive documentation for this {language} code:

```{language}
{code}
```

Create:
1. Function/class docstrings
2. Parameter descriptions
3. Return value documentation
4. Usage examples
5. Important notes or warnings

Follow {language} documentation conventions."""

    @staticmethod
    def build_security_analysis_prompt(code: str, context: Dict[str, Any]) -> str:
        """
        Build prompt for security analysis
        
        Args:
            code: Code to analyze
            context: Additional context
            
        Returns:
            Formatted prompt
        """
        language = context.get('language', 'unknown')
        
        return f"""Perform security analysis on this {language} code:

```{language}
{code}
```

Identify security vulnerabilities including:
1. Injection attacks (SQL, XSS, command injection)
2. Authentication/authorization issues
3. Data exposure and privacy concerns
4. Insecure cryptography
5. Dependency vulnerabilities

For each vulnerability:
- Severity rating (critical/high/medium/low)
- Detailed explanation
- Remediation steps
- Secure code example"""
