"""
CrewAI adapter for collaborative agent execution
Project Creator: Herman Swanepoel
"""

from __future__ import annotations

import asyncio
import textwrap
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Sequence, Tuple

from src.adapters.adapter_utils import AdapterExceptions, AdapterUtils

# pylint: disable=broad-except
from src.adapters.base_adapter import AgentAdapter, AgentConfig, Capability
from src.models import (
    AgentResponse,
    CodeContext,
    ConfidenceLevel,
    Suggestion,
    Task,
    TaskType,
)


@dataclass(frozen=True)
class CrewAIDependencies:
    """Container for CrewAI runtime dependencies."""

    agent_cls: Any
    crew_cls: Any
    process_enum: Any
    task_cls: Any


class CrewAIAdapter(AgentAdapter):
    """Adapter that orchestrates CrewAI agents for documentation and testing."""

    _CONFIDENCE_LOOKUP: Dict[ConfidenceLevel, float] = {
        ConfidenceLevel.HIGH: 0.85,
        ConfidenceLevel.MEDIUM: 0.6,
        ConfidenceLevel.LOW: 0.35,
    }

    def __init__(self, config: AgentConfig):
        super().__init__(config)
        self.llm: Optional[Any] = None
        self.doc_agent: Optional[Any] = None
        self.test_agent: Optional[Any] = None
        self.bug_agent: Optional[Any] = None
        self.crew: Optional[Any] = None
        self.agent_id: str = self.config.metadata.get("agent_id", "crewai_adapter")
        self._crewai_deps: Optional[CrewAIDependencies] = None
        self._ollama_cls: Optional[Any] = None

    async def initialize(self) -> None:
        """Initialise the CrewAI LLM and any available agents."""
        try:
            self._crewai_deps = self._crewai_deps or self._load_crewai_dependencies()
            self._ollama_cls = self._ollama_cls or self._load_ollama_client()

            if not self._crewai_deps:
                raise AdapterExceptions.AdapterInitializationError(
                    "CrewAI dependencies failed to load."
                )

            if not self._ollama_cls:
                raise AdapterExceptions.AdapterInitializationError(
                    "Ollama client failed to load."
                )

            self.llm = self._ollama_cls(
                model=self.config.metadata.get("model", "codellama:7b"),
                base_url=self.config.metadata.get(
                    "ollama_url", "http://localhost:11434"
                ),
            )

            if Capability.DOCUMENTATION in self.config.capabilities:
                self.doc_agent = self._crewai_deps.agent_cls(
                    role="Documentation Specialist",
                    goal="Generate clear, comprehensive documentation for code.",
                    backstory=textwrap.dedent(
                        """
                        You are an expert technical writer deeply versed in
                        software documentation best practices. You create docstrings,
                        README files, and API documentation that are clear, concise,
                        and helpful.
                        """
                    ).strip(),
                    llm=self.llm,
                    verbose=self.config.metadata.get("verbose", False),
                    allow_delegation=False,
                )

            if Capability.TESTING in self.config.capabilities:
                self.test_agent = self._crewai_deps.agent_cls(
                    role="Test Engineer",
                    goal="Generate thorough automated tests for supplied code.",
                    backstory=textwrap.dedent(
                        """
                        You are a senior test engineer with expertise in unit testing,
                        integration testing, and test-driven development. You write
                        test cases that cover edge conditions and reduce regressions.
                        """
                    ).strip(),
                    llm=self.llm,
                    verbose=self.config.metadata.get("verbose", False),
                    allow_delegation=False,
                )

            if Capability.BUG_DETECTION in self.config.capabilities:
                self.bug_agent = self._crewai_deps.agent_cls(
                    role="Bug Detection Specialist",
                    goal="Identify bugs, security vulnerabilities, and code quality issues.",
                    backstory=textwrap.dedent(
                        """
                        You are an expert security analyst and code reviewer with deep
                        knowledge of common vulnerabilities, bug patterns, and best
                        practices. You identify security issues like SQL injection, XSS,
                        command injection, hardcoded secrets, and logic errors. You
                        provide clear explanations and actionable fixes for all issues.
                        """
                    ).strip(),
                    llm=self.llm,
                    verbose=self.config.metadata.get("verbose", False),
                    allow_delegation=False,
                )

            self.is_initialized = True
        except Exception as exc:  # pragma: no cover - defensive guard
            raise AdapterExceptions.AdapterInitializationError(
                f"Failed to initialize CrewAI adapter: {exc}"
            ) from exc

    async def execute_task(self, task: Task, context: CodeContext) -> AgentResponse:
        """Execute a project task using CrewAI and convert the result."""
        if not self.is_initialized:
            await self.initialize()

        if not self.llm:
            raise RuntimeError("CrewAI adapter LLM not initialized")

        crew_setup = self._build_crew_setup(task, context)
        if not crew_setup:
            return AgentResponse(
                agent_id=self.agent_id,
                agent_name=self.config.name,
                suggestions=[],
                confidence=0.35,
                reasoning=(
                    "CrewAI adapter does not provide an agent for this task type."
                ),
                metadata={"task_id": task.id, "task_type": task.type.value},
            )

        if not self._crewai_deps:
            raise RuntimeError("CrewAI dependencies not initialized")

        agents, crew_tasks = crew_setup
        crew_instance = self._crewai_deps.crew_cls(
            agents=agents,
            tasks=crew_tasks,
            process=self._crewai_deps.process_enum.sequential,
            verbose=self.config.metadata.get("verbose", False),
        )
        self.crew = crew_instance

        kickoff_inputs = {
            "file_path": context.file_path,
            "language": context.language,
            "task_id": task.id,
        }

        try:
            kickoff_async = getattr(crew_instance, "kickoff_async", None)
            result: Any
            if callable(kickoff_async):
                async_result = kickoff_async(inputs=kickoff_inputs)
                if asyncio.iscoroutine(async_result):
                    result = await async_result
                else:
                    result = async_result
            else:
                kickoff_sync = getattr(crew_instance, "kickoff", None)
                if not callable(kickoff_sync):
                    raise AdapterExceptions.AdapterExecutionError(
                        "CrewAI crew has no kickoff entry point."
                    )
                result = await asyncio.to_thread(kickoff_sync, inputs=kickoff_inputs)
        except Exception as exc:  # noqa: BLE001
            return AgentResponse(
                agent_id=self.agent_id,
                agent_name=self.config.name,
                suggestions=[],
                confidence=0.0,
                reasoning=f"CrewAI execution failed: {exc}",
                metadata={"task_id": task.id, "task_type": task.type.value},
            )

        suggestions = self._parse_suggestions(result, task, context)
        confidence = self._determine_confidence(suggestions)
        reasoning = self._build_reasoning(result)

        metadata: Dict[str, Any] = {
            "task_id": task.id,
            "task_type": task.type.value,
            "crew_agents": [self._agent_role(agent) for agent in agents],
            "task_count": len(crew_tasks),
        }
        raw_text = getattr(result, "raw", None)
        if raw_text:
            metadata["raw_excerpt"] = AdapterUtils.truncate_output(
                str(raw_text),
                max_length=400,
            )

        token_usage = getattr(result, "token_usage", None)
        if token_usage:
            if hasattr(token_usage, "model_dump"):
                metadata["token_usage"] = token_usage.model_dump()
            elif hasattr(token_usage, "dict"):
                metadata["token_usage"] = token_usage.dict()
            else:
                metadata["token_usage"] = token_usage

        return AgentResponse(
            agent_id=self.agent_id,
            agent_name=self.config.name,
            suggestions=suggestions,
            confidence=confidence,
            reasoning=reasoning,
            metadata=metadata,
        )

    def _build_crew_setup(
        self, task: Task, context: CodeContext
    ) -> Optional[Tuple[List[Any], List[Any]]]:
        """Prepare CrewAI agents and tasks for the requested work."""
        agents: List[Any] = []
        crew_tasks: List[Any] = []

        if task.type == TaskType.DOCUMENTATION and self.doc_agent:
            agents.append(self.doc_agent)
            crew_tasks.append(
                self._create_crewai_task(
                    agent=self.doc_agent,
                    task=task,
                    context=context,
                    expected_output=(
                        "Markdown documentation summarising key behaviours, "
                        "public APIs, usage examples, and explicit assumptions."
                    ),
                )
            )

        if task.type == TaskType.TEST_GENERATION and self.test_agent:
            agents.append(self.test_agent)
            crew_tasks.append(
                self._create_crewai_task(
                    agent=self.test_agent,
                    task=task,
                    context=context,
                    expected_output=(
                        "Comprehensive automated tests with commentary on coverage and"
                        " edge cases."
                    ),
                )
            )

        if task.type == TaskType.BUG_DETECTION and self.bug_agent:
            agents.append(self.bug_agent)
            crew_tasks.append(
                self._create_crewai_task(
                    agent=self.bug_agent,
                    task=task,
                    context=context,
                    expected_output=(
                        "Detailed analysis of bugs, security vulnerabilities, and code "
                        "quality issues with severity levels, descriptions, and recommended "
                        "fixes for each issue found."
                    ),
                )
            )

        if not agents:
            return None

        return agents, crew_tasks

    def _create_crewai_task(
        self,
        agent: Any,
        task: Task,
        context: CodeContext,
        expected_output: str,
    ) -> Any:
        """Create a CrewAI Task definition using the supplied context."""
        code_snippet = context.code or task.content
        prompt_code = AdapterUtils.truncate_output(code_snippet or "(no code provided)")
        overview = task.description or task.metadata.get("prompt") or task.content

        description = textwrap.dedent(
            f"""
            {overview or 'Analyse the provided code and respond accordingly.'}

            Focus file: {context.file_path}
            Language: {context.language}

            Code to use as context:
            ```
            {prompt_code}
            ```
            """
        ).strip()

        label = task.type.value.replace("_", " ").title()

        if not self._crewai_deps:
            raise RuntimeError("CrewAI dependencies not initialized")

        return self._crewai_deps.task_cls(
            name=f"{label} - {self._agent_role(agent)}",
            description=description,
            expected_output=expected_output,
            agent=agent,
            markdown=True,
        )

    def _parse_suggestions(
        self, result: Any, task: Task, context: CodeContext
    ) -> List[Suggestion]:
        """Translate CrewAI output into project Suggestion models."""
        outputs: List[str] = []

        for task_output in getattr(result, "tasks_output", []) or []:
            outputs.append(getattr(task_output, "raw", "") or "")
            outputs.extend(self._extract_reasoning(task_output))

        raw_result = getattr(result, "raw", None)
        if raw_result:
            outputs.append(raw_result)

        combined = "\n\n".join(
            segment.strip() for segment in outputs if segment.strip()
        )
        if not combined:
            return []

        code_blocks = AdapterUtils.extract_code_blocks(combined)
        suggestions: List[Suggestion] = []

        if code_blocks:
            for code, description in code_blocks:
                score = 0.82 if code else 0.55
                suggestions.append(
                    Suggestion(
                        id=AdapterUtils.generate_suggestion_id("crewai"),
                        code=code or combined,
                        description=description
                        or self._default_suggestion_description(task.type, context),
                        confidence=AdapterUtils.map_confidence_score(score),
                        diff=None,
                        applicable_range=None,
                    )
                )
        else:
            suggestions.append(
                Suggestion(
                    id=AdapterUtils.generate_suggestion_id("crewai"),
                    code=combined,
                    description=self._default_suggestion_description(
                        task.type, context
                    ),
                    confidence=AdapterUtils.map_confidence_score(0.58),
                    diff=None,
                    applicable_range=None,
                )
            )

        return suggestions

    def _default_suggestion_description(
        self, task_type: TaskType, context: CodeContext
    ) -> str:
        if task_type == TaskType.DOCUMENTATION:
            return f"Documentation updates for {context.file_path}"
        if task_type == TaskType.TEST_GENERATION:
            return f"Test coverage recommendations for {context.file_path}"
        if task_type == TaskType.BUG_DETECTION:
            return f"Bug and security analysis for {context.file_path}"
        return f"CrewAI suggestion for {context.file_path}"

    def _extract_reasoning(self, task_output: Any) -> List[str]:
        reasoning: List[str] = []
        summary = getattr(task_output, "summary", None)
        if summary:
            reasoning.append(summary)
        description = getattr(task_output, "description", None)
        if description and description not in reasoning:
            reasoning.append(description)
        return reasoning

    def _determine_confidence(self, suggestions: Sequence[Suggestion]) -> float:
        if not suggestions:
            return 0.35

        scores = [
            self._CONFIDENCE_LOOKUP.get(suggestion.confidence, 0.35)
            for suggestion in suggestions
        ]
        return round(min(0.95, max(scores)), 2)

    def _build_reasoning(self, result: Any) -> str:
        tasks_output = getattr(result, "tasks_output", []) or []
        if not tasks_output:
            return AdapterUtils.truncate_output(
                getattr(result, "raw", "No output returned from CrewAI."),
                600,
            )

        lines: List[str] = []
        for index, task_output in enumerate(tasks_output, start=1):
            agent_name = getattr(task_output, "agent", "CrewAI Agent")
            summary = (
                getattr(task_output, "summary", None)
                or getattr(task_output, "description", None)
                or "Task completed."
            )
            raw_excerpt = AdapterUtils.truncate_output(
                getattr(task_output, "raw", "") or "",
                300,
            )
            if raw_excerpt:
                lines.append(f"Task {index} by {agent_name}: {summary}\n{raw_excerpt}")
            else:
                lines.append(f"Task {index} by {agent_name}: {summary}")

        return "\n\n".join(lines)

    async def get_capabilities(self) -> List[Capability]:
        return self.config.capabilities

    async def health_check(self) -> bool:
        if not self.is_initialized or not self.llm:
            return False

        try:
            response = await asyncio.to_thread(self.llm, "ping")
            return bool(response)
        except Exception:  # noqa: BLE001
            return False

    async def shutdown(self) -> None:
        self.llm = None
        self.doc_agent = None
        self.test_agent = None
        self.bug_agent = None
        self.crew = None
        await super().shutdown()

    def _agent_role(self, agent: Any) -> str:
        return getattr(agent, "role", self.config.name)

    def _load_crewai_dependencies(self) -> CrewAIDependencies:
        """Import CrewAI classes lazily so optional dependency issues surface gently."""
        try:
            from crewai import Agent as CrewAgent  # type: ignore[import]
            from crewai import Crew as CrewClass  # type: ignore[import]
            from crewai import Process  # type: ignore[import]
            from crewai import Task as CrewTask  # type: ignore[import]
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise AdapterExceptions.AdapterInitializationError(
                "CrewAI package is required for CrewAIAdapter but is not installed."
            ) from exc

        return CrewAIDependencies(
            agent_cls=CrewAgent,
            crew_cls=CrewClass,
            process_enum=Process,
            task_cls=CrewTask,
        )

    def _load_ollama_client(self) -> Any:
        """Import the LangChain Ollama client lazily."""
        try:
            from langchain_community.llms import Ollama  # type: ignore[import]
        except ImportError as exc:  # pragma: no cover - optional dependency
            raise AdapterExceptions.AdapterInitializationError(
                "LangChain community Ollama client is required but missing."
            ) from exc

        return Ollama


class CrewAIDocAgent(CrewAIAdapter):
    """Specialised CrewAI adapter for documentation generation."""

    def __init__(self):
        config = AgentConfig(
            name="CrewAI Doc Agent",
            description="Generates comprehensive documentation using CrewAI",
            capabilities=[Capability.DOCUMENTATION],
            enabled=True,
            max_concurrent=2,
            timeout=60,
            metadata={"model": "codellama:7b", "verbose": False},
        )
        super().__init__(config)


class CrewAITestAgent(CrewAIAdapter):
    """Specialised CrewAI adapter for test generation."""

    def __init__(self):
        config = AgentConfig(
            name="CrewAI Test Agent",
            description="Generates comprehensive test cases using CrewAI",
            capabilities=[Capability.TESTING],
            enabled=True,
            max_concurrent=2,
            timeout=60,
            metadata={"model": "codellama:7b", "verbose": False},
        )
        super().__init__(config)


class CrewAIBugAgent(CrewAIAdapter):
    """Specialised CrewAI adapter for bug detection and security analysis."""

    def __init__(self):
        config = AgentConfig(
            name="CrewAI Bug Agent",
            description="Detects bugs, security vulnerabilities, and code quality issues using CrewAI",
            capabilities=[Capability.BUG_DETECTION],
            enabled=True,
            max_concurrent=2,
            timeout=60,
            metadata={"model": "codellama:7b", "verbose": False},
        )
        super().__init__(config)

