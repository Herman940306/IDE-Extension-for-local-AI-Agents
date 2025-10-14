"""
Test Agent for automated test generation
Project Creator: Herman Swanepoel
"""

import logging
import re
from typing import List, Optional

from src.adapters.base_adapter import AgentAdapter
from src.models import AgentResponse, Suggestion, Task
from src.services.llm_manager import LLMManager

logger = logging.getLogger(__name__)


class TestAgent(AgentAdapter):
    """
    Specialized agent for test generation
    """

    def __init__(self, llm_manager: LLMManager):
        """
        Initialize Test Agent

        Args:
            llm_manager: LLM manager instance
        """
        super().__init__(
            name="test_agent",
            capabilities=["test_generation", "unit_tests", "integration_tests", "edge_cases"],
        )
        self.llm_manager = llm_manager

        logger.info("✓ TestAgent initialized")

    async def execute_task(self, task: Task) -> AgentResponse:
        """
        Execute test generation task

        Args:
            task: Task to execute

        Returns:
            AgentResponse with test suggestions
        """
        try:
            logger.info(f"TestAgent executing task: {task.id}")

            # Get code context
            code = task.code_context.get("code", "") if task.code_context else ""
            language = (
                task.code_context.get("language", "unknown") if task.code_context else "unknown"
            )

            if not code:
                return self._create_empty_response(task)

            # Determine test framework
            test_framework = self._determine_test_framework(language)

            # Generate tests
            suggestions = await self._generate_tests(code, language, test_framework)

            # Create response
            return AgentResponse(
                task_id=task.id,
                agent_name=self.name,
                suggestions=suggestions,
                metadata={
                    "test_framework": test_framework,
                    "language": language,
                    "test_count": len(suggestions),
                },
            )

        except Exception as e:
            logger.error(f"TestAgent task execution failed: {e}")
            return self._create_error_response(task, str(e))

    def _determine_test_framework(self, language: str) -> str:
        """
        Determine appropriate test framework for language

        Args:
            language: Programming language

        Returns:
            Test framework name
        """
        framework_map = {
            "python": "pytest",
            "javascript": "jest",
            "typescript": "jest",
            "java": "junit",
            "go": "testing",
            "rust": "cargo test",
        }

        return framework_map.get(language, "generic")

    async def _generate_tests(
        self, code: str, language: str, test_framework: str
    ) -> List[Suggestion]:
        """
        Generate test suggestions

        Args:
            code: Code to test
            language: Programming language
            test_framework: Test framework to use

        Returns:
            List of test suggestions
        """
        suggestions = []

        # Generate unit tests
        unit_test = await self._generate_unit_tests(code, language, test_framework)
        if unit_test:
            suggestions.append(unit_test)

        # Generate edge case tests
        edge_case_test = await self._generate_edge_case_tests(code, language, test_framework)
        if edge_case_test:
            suggestions.append(edge_case_test)

        # Generate integration test (if applicable)
        if self._needs_integration_test(code):
            integration_test = await self._generate_integration_tests(
                code, language, test_framework
            )
            if integration_test:
                suggestions.append(integration_test)

        return suggestions

    def _needs_integration_test(self, code: str) -> bool:
        """Check if code needs integration tests"""
        # Check for external dependencies, API calls, database operations
        integration_indicators = [
            r"import\s+requests",
            r"import\s+httpx",
            r"fetch\s*\(",
            r"axios\.",
            r"\.query\s*\(",
            r"\.execute\s*\(",
            r"database",
            r"api",
        ]

        return any(re.search(pattern, code, re.IGNORECASE) for pattern in integration_indicators)

    async def _generate_unit_tests(
        self, code: str, language: str, test_framework: str
    ) -> Optional[Suggestion]:
        """
        Generate unit tests

        Args:
            code: Code to test
            language: Programming language
            test_framework: Test framework

        Returns:
            Suggestion or None
        """
        try:
            prompt = f"""Generate comprehensive unit tests for this {language} code using {test_framework}:

```{language}
{code}
```

Generate tests that:
- Test normal/happy path scenarios
- Use appropriate assertions
- Follow {test_framework} best practices
- Are well-organized and readable
- Include setup/teardown if needed

Return only the test code, no explanations."""

            test_code = await self.llm_manager.generate(prompt)

            return Suggestion(
                code=test_code.strip(),
                description=f"Unit tests using {test_framework}",
                confidence=0.85,
                reasoning=f"Generated comprehensive unit tests covering normal scenarios",
            )

        except Exception as e:
            logger.error(f"Failed to generate unit tests: {e}")
            return None

    async def _generate_edge_case_tests(
        self, code: str, language: str, test_framework: str
    ) -> Optional[Suggestion]:
        """
        Generate edge case tests

        Args:
            code: Code to test
            language: Programming language
            test_framework: Test framework

        Returns:
            Suggestion or None
        """
        try:
            prompt = f"""Generate edge case tests for this {language} code using {test_framework}:

```{language}
{code}
```

Generate tests for:
- Boundary conditions
- Null/undefined/empty inputs
- Invalid inputs
- Error conditions
- Edge cases specific to the logic

Return only the test code, no explanations."""

            test_code = await self.llm_manager.generate(prompt)

            return Suggestion(
                code=test_code.strip(),
                description=f"Edge case tests using {test_framework}",
                confidence=0.8,
                reasoning="Generated tests for boundary conditions and error cases",
            )

        except Exception as e:
            logger.error(f"Failed to generate edge case tests: {e}")
            return None

    async def _generate_integration_tests(
        self, code: str, language: str, test_framework: str
    ) -> Optional[Suggestion]:
        """
        Generate integration tests

        Args:
            code: Code to test
            language: Programming language
            test_framework: Test framework

        Returns:
            Suggestion or None
        """
        try:
            prompt = f"""Generate integration tests for this {language} code using {test_framework}:

```{language}
{code}
```

Generate tests that:
- Test interactions with external systems
- Mock external dependencies appropriately
- Test end-to-end workflows
- Verify integration points

Return only the test code, no explanations."""

            test_code = await self.llm_manager.generate(prompt)

            return Suggestion(
                code=test_code.strip(),
                description=f"Integration tests using {test_framework}",
                confidence=0.75,
                reasoning="Generated tests for external integrations and workflows",
            )

        except Exception as e:
            logger.error(f"Failed to generate integration tests: {e}")
            return None

    def _create_empty_response(self, task: Task) -> AgentResponse:
        """Create empty response when no code provided"""
        return AgentResponse(
            task_id=task.id,
            agent_name=self.name,
            suggestions=[],
            metadata={"error": "No code provided for test generation"},
        )

    def _create_error_response(self, task: Task, error: str) -> AgentResponse:
        """Create error response"""
        return AgentResponse(
            task_id=task.id, agent_name=self.name, suggestions=[], metadata={"error": error}
        )

    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        return self.capabilities

    async def health_check(self) -> bool:
        """Check if agent is healthy"""
        try:
            await self.llm_manager.generate("test", max_tokens=10)
            return True
        except Exception as e:
            logger.warning(f"LLM health check failed: {e}")
            return False
