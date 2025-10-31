"""Test generation agent adapted to modern response models."""

import logging
import re
import uuid
from typing import List, Optional

from src.adapters.base_adapter import AgentAdapter, AgentConfig, Capability
from src.models import AgentResponse, CodeContext, ConfidenceLevel, Suggestion, Task
from src.services.llm_manager import LLMManager

logger = logging.getLogger(__name__)


class TestAgent(AgentAdapter):
    """Specialized agent for automated test generation."""

    def __init__(self, llm_manager: LLMManager, config: Optional[AgentConfig] = None):
        if config is None:
            config = AgentConfig(
                name="Test Generation Agent",
                description="Generates unit, edge-case, and integration tests for code snippets",  # noqa: E501
                capabilities=[Capability.TESTING],
                metadata={"supports": ["unit", "edge", "integration"]},
            )
        super().__init__(config)
        self.llm_manager = llm_manager

        logger.info(
            "✓ TestAgent initialized",
            extra={
                "agent_name": config.name,
                "capabilities": [cap.value for cap in config.capabilities],
            },
        )

    async def execute_task(self, task: Task, context: CodeContext) -> AgentResponse:
        """Execute test generation task using provided code context."""
        try:
            logger.info("TestAgent executing task", extra={"task_id": task.id})

            if not context.code:
                return self._create_empty_response(task)

            language = context.language or "unknown"
            test_framework = self._determine_test_framework(language)

            suggestions = await self._generate_tests(context.code, language, test_framework)

            confidence = self._calculate_confidence(suggestions)
            reasoning = self._build_reasoning(language, test_framework, suggestions)

            return AgentResponse(
                agent_id="test_agent",
                agent_name=self.config.name,
                suggestions=suggestions,
                confidence=confidence,
                reasoning=reasoning,
                metadata={
                    "task_id": task.id,
                    "test_framework": test_framework,
                    "language": language,
                    "test_count": len(suggestions),
                },
            )

        except Exception as exc:  # pragma: no cover - defensive logging
            logger.exception("TestAgent task execution failed", extra={"task_id": task.id})
            return self._create_error_response(task, str(exc))

    async def initialize(self) -> None:
        """Initialize the agent - no specific setup required."""
        pass

    async def get_capabilities(self) -> List[Capability]:
        """Get the capabilities of this agent."""
        return self.config.capabilities

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
        suggestions: List[Suggestion] = []

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
            prompt = (
                f"Generate comprehensive unit tests for this {language} code using"
                f" {test_framework}:\n\n"
                f"```{language}\n{code}\n```\n\n"
                "Generate tests that:\n"
                "- Test normal/happy path scenarios\n"
                "- Use appropriate assertions\n"
                f"- Follow {test_framework} best practices\n"
                "- Are well-organized and readable\n"
                "- Include setup/teardown if needed\n\n"
                "Return only the test code, no explanations."
            )

            test_code = await self.llm_manager.generate(prompt)

            return Suggestion(
                id=self._new_suggestion_id("unit"),
                code=test_code.strip(),
                description=f"Unit tests using {test_framework}",
                confidence=ConfidenceLevel.HIGH,
                diff=None,
                applicable_range=None,
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
            prompt = (
                f"Generate edge case tests for this {language} code using {test_framework}:\n\n"  # noqa: E501
                f"```{language}\n{code}\n```\n\n"
                "Generate tests for:\n"
                "- Boundary conditions\n"
                "- Null/undefined/empty inputs\n"
                "- Invalid inputs\n"
                "- Error conditions\n"
                "- Edge cases specific to the logic\n\n"
                "Return only the test code, no explanations."
            )

            test_code = await self.llm_manager.generate(prompt)

            return Suggestion(
                id=self._new_suggestion_id("edge"),
                code=test_code.strip(),
                description=f"Edge case tests using {test_framework}",
                confidence=ConfidenceLevel.MEDIUM,
                diff=None,
                applicable_range=None,
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
            prompt = (
                f"Generate integration tests for this {language} code using {test_framework}:\n\n"  # noqa: E501
                f"```{language}\n{code}\n```\n\n"
                "Generate tests that:\n"
                "- Test interactions with external systems\n"
                "- Mock external dependencies appropriately\n"
                "- Test end-to-end workflows\n"
                "- Verify integration points\n\n"
                "Return only the test code, no explanations."
            )

            test_code = await self.llm_manager.generate(prompt)

            return Suggestion(
                id=self._new_suggestion_id("integration"),
                code=test_code.strip(),
                description=f"Integration tests using {test_framework}",
                confidence=ConfidenceLevel.MEDIUM,
                diff=None,
                applicable_range=None,
            )

        except Exception as e:
            logger.error(f"Failed to generate integration tests: {e}")
            return None

    def _create_empty_response(self, task: Task) -> AgentResponse:
        return AgentResponse(
            agent_id="test_agent",
            agent_name=self.config.name,
            suggestions=[],
            confidence=0.0,
            reasoning="No code provided for test generation",
            metadata={"task_id": task.id, "error": "missing_code"},
        )

    def _create_error_response(self, task: Task, error: str) -> AgentResponse:
        return AgentResponse(
            agent_id="test_agent",
            agent_name=self.config.name,
            suggestions=[],
            confidence=0.0,
            reasoning=f"Test generation failed: {error}",
            metadata={"task_id": task.id, "error": error},
        )

    def _calculate_confidence(self, suggestions: List[Suggestion]) -> float:
        if not suggestions:
            return 0.0

        values = [self._confidence_to_float(s.confidence) for s in suggestions]
        return sum(values) / len(values)

    def _build_reasoning(self, language: str, framework: str, suggestions: List[Suggestion]) -> str:
        if not suggestions:
            return "No actionable test scenarios identified."

        summary = [
            "Generated automated tests:",
            f"- Language: {language}",
            f"- Framework: {framework}",
        ]
        for suggestion in suggestions:
            summary.append(f"- {suggestion.description}")
        return "\n".join(summary)

    def _confidence_to_float(self, level: ConfidenceLevel) -> float:
        mapping = {
            ConfidenceLevel.HIGH: 0.9,
            ConfidenceLevel.MEDIUM: 0.7,
            ConfidenceLevel.LOW: 0.4,
        }
        return mapping.get(level, 0.4)

    def _new_suggestion_id(self, category: str) -> str:
        return f"test_{category}_{uuid.uuid4().hex[:8]}"

    async def health_check(self) -> bool:
        try:
            await self.llm_manager.generate("ping", max_tokens=8)
            return True
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("LLM health check failed", extra={"error": str(exc)})
            return False
