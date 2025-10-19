"""
Documentation Generation Agent
Project Creator: Herman Swanepoel
"""

import ast
import logging
import re
import uuid
from typing import List, Optional, Union

from src.adapters.base_adapter import AgentAdapter, AgentConfig, Capability
from src.adapters.crewai_adapter import CrewAIDocAgent
from src.models import (
    AgentResponse,
    CodeContext,
    ConfidenceLevel,
    Priority,
    Suggestion,
    Task,
    TaskType,
)
from src.services.llm_manager import LLMManager

logger = logging.getLogger(__name__)


class DocAgent(AgentAdapter):
    """
    Documentation generation agent

    Generates docstrings, README files, API documentation, and code comments
    using CrewAI for collaborative documentation generation.
    """

    def __init__(
        self,
        llm_manager: Optional[LLMManager] = None,
        crewai_adapter: Optional[CrewAIDocAgent] = None,
        config: Optional[AgentConfig] = None,
    ):
        """Initialize the documentation agent."""
        config = config or AgentConfig(
            name="Documentation Agent",
            description="Generates docstrings, READMEs, API docs, and code comments",
            capabilities=[Capability.DOCUMENTATION],
            metadata={"supports": ["docstring", "readme", "api", "comments"]},
        )
        super().__init__(config)

        self.llm_manager = llm_manager
        self.crewai_adapter = crewai_adapter or CrewAIDocAgent()

        logger.info(
            "✓ DocAgent initialized",
            extra={
                "agent_name": config.name,
                "capabilities": [cap.value for cap in config.capabilities],
            },
        )

    async def initialize(self) -> None:
        if self.is_initialized:
            return

        if self.crewai_adapter and not self.crewai_adapter.is_initialized:
            await self.crewai_adapter.initialize()

        self.is_initialized = True
        logger.info("✓ DocAgent ready")

    async def execute_task(self, task: Task, context: CodeContext) -> AgentResponse:
        """Generate documentation suggestions based on the provided task and context."""
        if not self.is_initialized:
            await self.initialize()

        try:
            if not context.code:
                return self._create_empty_response(task)

            doc_type = self._determine_doc_type(task, context)

            if doc_type == "docstring":
                suggestions = await self._generate_docstrings(context)
            elif doc_type == "readme":
                suggestions = await self._generate_readme(context)
            elif doc_type == "api":
                suggestions = await self._generate_api_docs(context)
            elif doc_type == "comments":
                suggestions = await self._generate_comments(context)
            else:
                return await self._execute_general_documentation(task, context)

            confidence = self._calculate_confidence(suggestions)

            return AgentResponse(
                agent_id="doc_agent",
                agent_name=self.config.name,
                suggestions=suggestions,
                confidence=confidence,
                reasoning=f"Generated {doc_type} documentation",
                metadata={
                    "task_id": task.id,
                    "doc_type": doc_type,
                    "suggestion_count": len(suggestions),
                },
            )

        except Exception as exc:  # pragma: no cover - defensive guard
            logger.exception("DocAgent execution failed", extra={"task_id": task.id})
            return self._create_error_response(task, str(exc))

    async def get_capabilities(self) -> List[Capability]:
        return self.config.capabilities

    async def health_check(self) -> bool:
        try:
            if self.llm_manager:
                await self.llm_manager.generate("ping", max_tokens=8)

            if self.crewai_adapter:
                return await self.crewai_adapter.health_check()

            return True
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("DocAgent health check failed", extra={"error": str(exc)})
            return False

    async def shutdown(self) -> None:
        if self.crewai_adapter:
            await self.crewai_adapter.shutdown()
        await super().shutdown()

    def _determine_doc_type(self, task: Task, context: CodeContext) -> str:
        """Determine what type of documentation to generate"""
        description_lower = (task.description or "").lower()

        if "docstring" in description_lower or "function doc" in description_lower:
            return "docstring"
        elif "readme" in description_lower:
            return "readme"
        elif "api" in description_lower:
            return "api"
        elif "comment" in description_lower:
            return "comments"
        else:
            return "general"

    async def _generate_docstrings(self, context: CodeContext) -> List[Suggestion]:
        """Generate docstrings for functions and classes"""
        suggestions = []

        if context.language == "python":
            suggestions = await self._generate_python_docstrings(context)
        elif context.language in ["javascript", "typescript"]:
            suggestions = await self._generate_jsdoc(context)

        return suggestions

    async def _generate_python_docstrings(self, context: CodeContext) -> List[Suggestion]:
        """Generate Python docstrings"""
        if not context.code:
            return []

        try:
            tree = ast.parse(context.code)
        except SyntaxError:
            # If parsing fails we cannot offer structured docstrings
            return []

        suggestions: List[Suggestion] = []

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                if not ast.get_docstring(node):
                    docstring = self._create_python_docstring(node)
                    start_line = getattr(node, "lineno", 1)
                    end_line = getattr(node, "end_lineno", start_line)

                    suggestions.append(
                        Suggestion(
                            id=f"docstring_{node.name}_{uuid.uuid4().hex[:8]}",
                            code=docstring,
                            description=(
                                "Add Google-style docstring for "
                                f"{type(node).__name__} '{node.name}'"
                            ),
                            confidence=ConfidenceLevel.MEDIUM,
                            diff=None,
                            applicable_range={
                                "start": {"line": start_line, "character": 0},
                                "end": {"line": end_line, "character": 0},
                            },
                        )
                    )

        return suggestions

    def _create_python_docstring(self, node: ast.AST) -> str:
        """Create a Python docstring for a function or class"""
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            return self._create_function_docstring(node)
        if isinstance(node, ast.ClassDef):
            return self._create_class_docstring(node)
        return '    """TODO: Add docstring"""\n'

    def _create_function_docstring(self, node: Union[ast.FunctionDef, ast.AsyncFunctionDef]) -> str:
        """Create docstring for a function"""
        # Extract parameters
        params = []
        for arg in node.args.args:
            arg_name = arg.arg
            arg_type = "Any"
            if arg.annotation:
                arg_type = ast.unparse(arg.annotation)
            params.append((arg_name, arg_type))

        # Extract return type
        return_type = "None"
        if node.returns:
            return_type = ast.unparse(node.returns)

        # Build docstring
        docstring_lines = [
            '    """',
            f"    {node.name.replace('_', ' ').title()}",
            "",
        ]

        if params:
            docstring_lines.append("    Args:")
            for param_name, param_type in params:
                if param_name != "self":
                    docstring_lines.append(
                        f"        {param_name} ({param_type}): Description of {param_name}"  # noqa: E501
                    )

        if return_type != "None":
            docstring_lines.extend(
                [
                    "",
                    "    Returns:",
                    f"        {return_type}: Description of return value",
                ]
            )

        # Check for exceptions
        has_raises = any(isinstance(n, ast.Raise) for n in ast.walk(node))
        if has_raises:
            docstring_lines.extend(
                [
                    "",
                    "    Raises:",
                    "        Exception: Description of exception",
                ]
            )

        docstring_lines.append('    """')

        return "\n".join(docstring_lines) + "\n"

    def _create_class_docstring(self, node: ast.ClassDef) -> str:
        """Create docstring for a class"""
        docstring_lines = [
            '    """',
            f"    {node.name.replace('_', ' ').title()}",
            "",
            f"    Description of {node.name} class.",
            "",
        ]

        # Find __init__ method
        init_method = None
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                init_method = item
                break

        if init_method and init_method.args.args:
            docstring_lines.append("    Attributes:")
            for arg in init_method.args.args:
                if arg.arg != "self":
                    arg_type = "Any"
                    if arg.annotation:
                        arg_type = ast.unparse(arg.annotation)
                    docstring_lines.append(
                        f"        {arg.arg} ({arg_type}): Description of {arg.arg}"
                    )

        docstring_lines.append('    """')

        return "\n".join(docstring_lines) + "\n"

    async def _generate_jsdoc(self, context: CodeContext) -> List[Suggestion]:
        """Generate JSDoc comments for JavaScript/TypeScript"""
        suggestions = []

        # Find functions without JSDoc
        function_pattern = (
            r"(?:async\s+)?(?:function\s+(\w+)|"
            r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>)"
        )

        for match in re.finditer(function_pattern, context.code):
            func_name = match.group(1) or match.group(2)

            # Check if JSDoc already exists
            lines_before = context.code[: match.start()].split("\n")
            has_jsdoc = any("/**" in line for line in lines_before[-3:])

            if not has_jsdoc:
                jsdoc = self._create_jsdoc(func_name, match.group(0))
                line_num = context.code[: match.start()].count("\n") + 1

                suggestions.append(
                    Suggestion(
                        id=f"jsdoc_{func_name}_{uuid.uuid4().hex[:8]}",
                        code=jsdoc,
                        description=f"Add JSDoc for {func_name}",
                        confidence=ConfidenceLevel.MEDIUM,
                        diff=None,
                        applicable_range={
                            "start": {"line": line_num, "character": 0},
                            "end": {"line": line_num, "character": 0},
                        },
                    )
                )

        return suggestions

    def _create_jsdoc(self, func_name: str, func_signature: str) -> str:
        """Create JSDoc comment"""
        # Extract parameters
        param_match = re.search(r"\(([^)]*)\)", func_signature)
        params = []
        if param_match:
            param_str = param_match.group(1)
            if param_str.strip():
                params = [p.strip().split(":")[0].strip() for p in param_str.split(",")]

        jsdoc = "/**\n"
        jsdoc += f' * {func_name.replace("_", " ").title()}\n'
        jsdoc += " *\n"

        for param in params:
            if param:
                jsdoc += f" * @param {{{param}}} {param} - Description of {param}\n"

        jsdoc += " * @returns {{*}} Description of return value\n"
        jsdoc += " */\n"

        return jsdoc

    async def _generate_readme(self, context: CodeContext) -> List[Suggestion]:
        """Generate README documentation"""
        # Use CrewAI for comprehensive README generation
        if self.crewai_adapter:
            task = Task(
                id="readme_gen",
                type=TaskType.DOCUMENTATION,
                content=context.code or context.surrounding_code or "",
                description="Generate comprehensive README documentation",
                priority=Priority.HIGH,
                context={
                    "file_path": context.file_path,
                    "language": context.language,
                },
                metadata={"doc_type": "readme"},
            )
            response = await self.crewai_adapter.execute_task(task, context)
            return response.suggestions

        # Fallback: Generate basic README template
        readme = self._create_readme_template(context)

        return [
            Suggestion(
                id=f"readme_{uuid.uuid4().hex[:8]}",
                code=readme,
                description="README.md template",
                confidence=ConfidenceLevel.LOW,
                diff=None,
                applicable_range=None,
            )
        ]

    def _create_readme_template(self, context: CodeContext) -> str:
        """Create basic README template"""
        file_name = context.file_path.split("/")[-1]
        project_name = file_name.replace(".py", "").replace(".js", "").replace(".ts", "").title()

        readme = f"""# {project_name}

## Description

Brief description of the project.

## Installation

```bash
# Installation instructions
```

## Usage

```{context.language}
# Usage examples
```

## Features

- Feature 1
- Feature 2
- Feature 3

## API Documentation

### Main Functions

#### function_name()

Description of function.

**Parameters:**
- `param1` (type): Description

**Returns:**
- type: Description

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

MIT License

## Author

Project Creator: Herman Swanepoel
"""

        return readme

    async def _generate_api_docs(self, context: CodeContext) -> List[Suggestion]:
        """Generate API documentation"""
        # Use CrewAI for comprehensive API docs
        if self.crewai_adapter:
            task = Task(
                id="api_docs_gen",
                type=TaskType.DOCUMENTATION,
                content=context.code or context.surrounding_code or "",
                description="Generate comprehensive API documentation",
                priority=Priority.HIGH,
                context={
                    "file_path": context.file_path,
                    "language": context.language,
                },
                metadata={"doc_type": "api"},
            )
            response = await self.crewai_adapter.execute_task(task, context)
            return response.suggestions

        return []

    async def _generate_comments(self, context: CodeContext) -> List[Suggestion]:
        """Generate inline code comments"""
        suggestions = []

        # Find complex code blocks that need comments
        lines = context.code.split("\n")

        for i, line in enumerate(lines):
            # Skip lines that already have comments
            if "#" in line or "//" in line:
                continue

            # Check for complex patterns
            if self._is_complex_line(line):
                comment = "# TODO: Add comment explaining this logic"
                line_number = i + 1

                suggestions.append(
                    Suggestion(
                        id=f"comment_{line_number}_{uuid.uuid4().hex[:8]}",
                        code=f"{comment}\n{line}",
                        description=f"Add comment for line {line_number}",
                        confidence=ConfidenceLevel.LOW,
                        diff=None,
                        applicable_range={
                            "start": {"line": line_number, "character": 0},
                            "end": {"line": line_number, "character": 0},
                        },
                    )
                )

        return suggestions[:10]  # Limit to top 10

    def _is_complex_line(self, line: str) -> bool:
        """Check if a line is complex and needs a comment"""
        # Check for complex patterns
        complex_patterns = [
            r"lambda\s+",  # Lambda functions
            r"\[.*for.*in.*\]",  # List comprehensions
            r"\{.*for.*in.*\}",  # Dict comprehensions
            r".*\?.*:.*",  # Ternary operators
            r".*&&.*\|\|.*",  # Complex boolean logic
        ]

        return any(re.search(pattern, line) for pattern in complex_patterns)

    def _calculate_confidence(self, suggestions: List[Suggestion]) -> float:
        """Calculate overall confidence"""
        if not suggestions:
            return 0.5

        values = [self._confidence_to_float(s.confidence) for s in suggestions]
        return sum(values) / len(values)

    def _confidence_to_float(self, level: ConfidenceLevel) -> float:
        mapping = {
            ConfidenceLevel.HIGH: 0.9,
            ConfidenceLevel.MEDIUM: 0.7,
            ConfidenceLevel.LOW: 0.4,
        }
        return mapping.get(level, 0.5)

    def _create_empty_response(self, task: Task) -> AgentResponse:
        return AgentResponse(
            agent_id="doc_agent",
            agent_name=self.config.name,
            suggestions=[],
            confidence=0.0,
            reasoning="No code provided for documentation generation",
            metadata={"task_id": task.id, "error": "missing_code"},
        )

    def _create_error_response(self, task: Task, error: str) -> AgentResponse:
        return AgentResponse(
            agent_id="doc_agent",
            agent_name=self.config.name,
            suggestions=[],
            confidence=0.0,
            reasoning=f"Documentation generation failed: {error}",
            metadata={"task_id": task.id, "error": error},
        )

    async def _execute_general_documentation(
        self, task: Task, context: CodeContext
    ) -> AgentResponse:
        if self.crewai_adapter:
            crew_response = await self.crewai_adapter.execute_task(task, context)
            suggestions = crew_response.suggestions
            confidence = self._calculate_confidence(suggestions)
            metadata = {
                "task_id": task.id,
                "source": "crewai",
                **getattr(crew_response, "metadata", {}),
            }

            return AgentResponse(
                agent_id="doc_agent",
                agent_name=self.config.name,
                suggestions=suggestions,
                confidence=confidence,
                reasoning="Delegated documentation generation to CrewAI workflow",
                metadata=metadata,
            )

        return AgentResponse(
            agent_id="doc_agent",
            agent_name=self.config.name,
            suggestions=[],
            confidence=0.0,
            reasoning="No documentation strategy available for this task",
            metadata={"task_id": task.id, "error": "unsupported_doc_type"},
        )
