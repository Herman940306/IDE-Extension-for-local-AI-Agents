"""
Documentation Generation Agent
Project Creator: Herman Swanepoel
"""

import ast
import re
from typing import List, Optional

from src.adapters.crewai_adapter import CrewAIDocAgent
from src.models import AgentResponse, CodeContext, Suggestion, Task


class DocAgent:
    """
    Documentation generation agent

    Generates docstrings, README files, API documentation, and code comments
    using CrewAI for collaborative documentation generation.
    """

    def __init__(self, crewai_adapter: Optional[CrewAIDocAgent] = None):
        """
        Initialize Doc Agent

        Args:
            crewai_adapter: Optional CrewAI adapter for collaborative doc generation
        """
        self.name = "Doc Agent"
        self.crewai_adapter = crewai_adapter or CrewAIDocAgent()

    async def generate_documentation(self, task: Task, context: CodeContext) -> AgentResponse:
        """
        Generate documentation for code

        Args:
            task: Task to execute
            context: Code context

        Returns:
            AgentResponse with documentation suggestions
        """
        try:
            # Determine documentation type
            doc_type = self._determine_doc_type(task, context)

            # Generate documentation based on type
            if doc_type == "docstring":
                suggestions = await self._generate_docstrings(context)
            elif doc_type == "readme":
                suggestions = await self._generate_readme(context)
            elif doc_type == "api":
                suggestions = await self._generate_api_docs(context)
            elif doc_type == "comments":
                suggestions = await self._generate_comments(context)
            else:
                # Use CrewAI for general documentation
                return await self.crewai_adapter.execute_task(task, context)

            confidence = self._calculate_confidence(suggestions)

            return AgentResponse(
                task_id=task.id,
                agent_name=self.name,
                suggestions=suggestions,
                confidence=confidence,
                reasoning=f"Generated {doc_type} documentation",
            )

        except Exception as e:
            return AgentResponse(
                task_id=task.id,
                agent_name=self.name,
                suggestions=[],
                confidence=0.0,
                reasoning=f"Documentation generation failed: {str(e)}",
            )

    def _determine_doc_type(self, task: Task, context: CodeContext) -> str:
        """Determine what type of documentation to generate"""
        description_lower = task.description.lower()

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
        suggestions = []

        try:
            # Parse Python code
            tree = ast.parse(context.code)

            # Find functions and classes without docstrings
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                    if not ast.get_docstring(node):
                        docstring = self._create_python_docstring(node, context)

                        # Find insertion point
                        node.lineno

                        suggestions.append(
                            Suggestion(
                                code=docstring,
                                description=f"Add docstring for {node.name}",
                                confidence=0.85,
                                reasoning=f"Generated Google-style docstring for {type(node).__name__} '{node.name}'",
                            )
                        )

        except SyntaxError:
            # If parsing fails, use CrewAI
            pass

        return suggestions

    def _create_python_docstring(self, node: ast.AST, context: CodeContext) -> str:
        """Create a Python docstring for a function or class"""
        if isinstance(node, ast.FunctionDef):
            return self._create_function_docstring(node)
        elif isinstance(node, ast.ClassDef):
            return self._create_class_docstring(node)
        return '"""TODO: Add docstring"""'

    def _create_function_docstring(self, node: ast.FunctionDef) -> str:
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
        docstring = f'    """\n'
        docstring += f'    {node.name.replace("_", " ").title()}\n\n'

        if params:
            docstring += "    Args:\n"
            for param_name, param_type in params:
                if param_name != "self":
                    docstring += (
                        f"        {param_name} ({param_type}): Description of {param_name}\n"
                    )

        if return_type != "None":
            docstring += f"\n    Returns:\n"
            docstring += f"        {return_type}: Description of return value\n"

        # Check for exceptions
        has_raises = any(isinstance(n, ast.Raise) for n in ast.walk(node))
        if has_raises:
            docstring += "\n    Raises:\n"
            docstring += "        Exception: Description of exception\n"

        docstring += '    """\n'

        return docstring

    def _create_class_docstring(self, node: ast.ClassDef) -> str:
        """Create docstring for a class"""
        docstring = f'    """\n'
        docstring += f'    {node.name.replace("_", " ").title()}\n\n'
        docstring += f"    Description of {node.name} class.\n\n"

        # Find __init__ method
        init_method = None
        for item in node.body:
            if isinstance(item, ast.FunctionDef) and item.name == "__init__":
                init_method = item
                break

        if init_method and init_method.args.args:
            docstring += "    Attributes:\n"
            for arg in init_method.args.args:
                if arg.arg != "self":
                    arg_type = "Any"
                    if arg.annotation:
                        arg_type = ast.unparse(arg.annotation)
                    docstring += f"        {arg.arg} ({arg_type}): Description of {arg.arg}\n"

        docstring += '    """\n'

        return docstring

    async def _generate_jsdoc(self, context: CodeContext) -> List[Suggestion]:
        """Generate JSDoc comments for JavaScript/TypeScript"""
        suggestions = []

        # Find functions without JSDoc
        function_pattern = r"(?:async\s+)?(?:function\s+(\w+)|(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*=>)"

        for match in re.finditer(function_pattern, context.code):
            func_name = match.group(1) or match.group(2)
            line_num = context.code[: match.start()].count("\n") + 1

            # Check if JSDoc already exists
            lines_before = context.code[: match.start()].split("\n")
            has_jsdoc = any("/**" in line for line in lines_before[-3:])

            if not has_jsdoc:
                jsdoc = self._create_jsdoc(func_name, match.group(0))

                suggestions.append(
                    Suggestion(
                        code=jsdoc,
                        description=f"Add JSDoc for {func_name}",
                        confidence=0.85,
                        reasoning=f"Generated JSDoc comment for function '{func_name}'",
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
                type="documentation",
                description="Generate comprehensive README documentation",
                priority="high",
            )
            response = await self.crewai_adapter.execute_task(task, context)
            return response.suggestions

        # Fallback: Generate basic README template
        readme = self._create_readme_template(context)

        return [
            Suggestion(
                code=readme,
                description="README.md template",
                confidence=0.7,
                reasoning="Generated basic README template",
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
                type="documentation",
                description="Generate comprehensive API documentation",
                priority="high",
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
                comment = f"# TODO: Add comment explaining this logic"

                suggestions.append(
                    Suggestion(
                        code=f"{comment}\n{line}",
                        description=f"Add comment for line {i+1}",
                        confidence=0.6,
                        reasoning="Complex code detected, comment recommended",
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

        avg_confidence = sum(s.confidence for s in suggestions) / len(suggestions)
        return avg_confidence
