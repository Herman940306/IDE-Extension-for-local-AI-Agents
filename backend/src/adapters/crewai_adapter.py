"""
CrewAI adapter for collaborative agent execution
Project Creator: Herman Swanepoel
"""

import asyncio
import importlib
import textwrap
from typing import Any, List, Optional

from src.adapters.adapter_utils import AdapterUtils
from src.adapters.base_adapter import AgentAdapter, AgentConfig, Capability
from src.models import AgentResponse, CodeContext, Suggestion, Task

CREWAI_DEPENDENCIES_AVAILABLE = True

Agent: Any = None
Crew: Any = None
Process: Any = None
CrewTask: Any = None
Ollama: Any = None

try:  # Optional dependency loaded lazily to avoid hard requirement
    crewai_module = importlib.import_module("crewai")
    Agent = getattr(crewai_module, "Agent", None)
    Crew = getattr(crewai_module, "Crew", None)
    Process = getattr(crewai_module, "Process", None)
    CrewTask = getattr(crewai_module, "Task", None)
    if not all([Agent, Crew, Process, CrewTask]):
        CREWAI_DEPENDENCIES_AVAILABLE = False
except ImportError:  # pragma: no cover - optional path
    CREWAI_DEPENDENCIES_AVAILABLE = False

try:  # Optional dependency loaded lazily to avoid hard requirement
    langchain_module = importlib.import_module("langchain_community.llms")
    Ollama = getattr(langchain_module, "Ollama", None)
    if Ollama is None:
        CREWAI_DEPENDENCIES_AVAILABLE = False
except ImportError:  # pragma: no cover - optional path
    CREWAI_DEPENDENCIES_AVAILABLE = False

MISSING_DEPENDENCIES_MESSAGE = (
    "CrewAI adapter requires optional dependencies `crewai` and `langchain`. "
    "Install them to enable CrewAI integration."
)


class CrewAIAdapter(AgentAdapter):
    """
    Adapter for CrewAI framework

    Enables collaborative multi-agent execution using CrewAI's crew system.
    Supports Doc Agent and Test Agent for documentation and test generation.
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize CrewAI adapter

        Args:
            config: Agent configuration
        """
        super().__init__(config)
        self._dependencies_available = CREWAI_DEPENDENCIES_AVAILABLE
        self.llm: Optional[Any] = None
        self.doc_agent: Optional[Any] = None
        self.test_agent: Optional[Any] = None
        self.crew: Optional[Any] = None
        self.agent_id: str = self.config.metadata.get("agent_id", "crewai_adapter")

    async def initialize(self) -> None:
        """Initialize CrewAI agents and crew"""
        if not self._dependencies_available:
            raise RuntimeError(MISSING_DEPENDENCIES_MESSAGE)

        try:
            # Initialize LLM
            self.llm = Ollama(
                model=self.config.metadata.get("model", "codellama:7b"),
                base_url=self.config.metadata.get(
                    "ollama_url", "http://localhost:11434"
                ),
            )

            # Create Doc Agent
            if Capability.DOCUMENTATION in self.config.capabilities:
                self.doc_agent = Agent(
                    role="Documentation Specialist",
                    goal="Generate clear, comprehensive documentation for code",
                    backstory=textwrap.dedent(
                        """
                        You are an expert technical writer with deep knowledge of software  # noqa: E501
                        documentation best practices. You excel at creating docstrings, README  # noqa: E501
                        files, and API documentation that are clear, concise, and helpful.  # noqa: E501
                        """
                    ).strip(),
                    llm=self.llm,
                    verbose=self.config.metadata.get("verbose", False),
                    allow_delegation=False,
                )

            # Create Test Agent
            if Capability.TESTING in self.config.capabilities:
                self.test_agent = Agent(
                    role="Test Engineer",
                    goal="Generate comprehensive test cases for code",
                    backstory=textwrap.dedent(
                        """
                        You are a senior test engineer with expertise in unit testing, integration  # noqa: E501
                        testing, and test-driven development. You write thorough test cases that  # noqa: E501
                        cover edge cases and ensure code reliability.
                        """
                    ).strip(),
                    llm=self.llm,
                    verbose=self.config.metadata.get("verbose", False),
                    allow_delegation=False,
                )

            self.is_initialized = True

        except Exception as e:
            raise Exception(f"Failed to initialize CrewAI adapter: {e}") from e

    async def execute_task(self, task: Task, context: CodeContext) -> AgentResponse:
        """
        Execute a task using CrewAI crew

        Args:
            task: Task to execute
            context: Code context

        Returns:
            AgentResponse with suggestions
        """
        if not self._dependencies_available:
            return AgentResponse(
                agent_id=self.agent_id,
                agent_name=self.config.name,
                suggestions=[],
                confidence=0.0,
                reasoning=MISSING_DEPENDENCIES_MESSAGE,
                metadata={"task_id": task.id, "error": "crewai_dependencies_missing"},
            )

        if not self.is_initialized:
            await self.initialize()

        try:
            # Convert task to CrewAI format
            crew_task = self._convert_to_crew_task(task, context)

            # Select appropriate agent(s)
            agents = self._select_agents(task)

            if not agents:
                return AgentResponse(
                    agent_id=self.agent_id,
                    agent_name=self.config.name,
                    suggestions=[],
                    confidence=0.0,
                    reasoning="No suitable CrewAI agents available for this task type",
                    metadata={"task_id": task.id, "error": "no_agents"},
                )

            # Create and execute crew
            crew = Crew(
                agents=agents,
                tasks=[crew_task],
                process=Process.sequential,
                verbose=self.config.metadata.get("verbose", False),
            )

            # Execute in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            result = await loop.run_in_executor(None, crew.kickoff)

            # Parse and convert result
            return self._convert_crew_result(result, task)

        except Exception as e:
            return AgentResponse(
                agent_id=self.agent_id,
                agent_name=self.config.name,
                suggestions=[],
                confidence=0.0,
                reasoning=f"CrewAI task execution failed: {str(e)}",
                metadata={"task_id": task.id, "error": str(e)},
            )

    @property
    def dependencies_available(self) -> bool:
        """Expose whether optional CrewAI dependencies are ready for use."""
        return self._dependencies_available

    def _convert_to_crew_task(self, task: Task, context: CodeContext) -> Any:
        """
        Convert our task format to CrewAI task format

        Args:
            task: Our task format
            context: Code context

        Returns:
            CrewAI task
        """
        # Build task description
        description = f"""
Task: {task.type.value}
Priority: {task.priority.value}

Code Context:
File: {context.file_path}
Language: {context.language}

Code:
```{context.language}
{context.code}
```

Requirements:
{task.description}

Please provide your response in the following format:
1. Analysis of the code
2. Specific suggestions or generated content
3. Reasoning for your recommendations
"""

        if context.selected_text:
            description += f"\n\nSelected Code:\n```{context.language}\n{context.selected_text}\n```"  # noqa: E501

        return CrewTask(
            description=description,
            expected_output="Detailed analysis and actionable suggestions or generated content",  # noqa: E501
        )

    def _select_agents(self, task: Task) -> List[Any]:
        """
        Select appropriate agents for the task

        Args:
            task: Task to execute

        Returns:
            List of agents to use
        """
        agents = []

        if task.type.value == "documentation" and self.doc_agent:
            agents.append(self.doc_agent)
        elif task.type.value == "test_generation" and self.test_agent:
            agents.append(self.test_agent)
        elif task.type.value == "refactor":
            # For refactoring, we might want both doc and test agents
            if self.doc_agent:
                agents.append(self.doc_agent)
            if self.test_agent:
                agents.append(self.test_agent)

        return agents

    def _convert_crew_result(self, result: Any, task: Task) -> AgentResponse:
        """
        Convert CrewAI result to our response format

        Args:
            result: CrewAI execution result
            task: Original task

        Returns:
            AgentResponse
        """
        try:
            # Parse the result text
            result_text = str(result)

            # Extract suggestions from result
            suggestions = self._parse_suggestions(result_text)

            # Calculate confidence based on result quality
            confidence = self._calculate_confidence(result_text, suggestions)

            return AgentResponse(
                agent_id=self.agent_id,
                agent_name=self.config.name,
                suggestions=suggestions,
                confidence=confidence,
                reasoning=result_text.strip() or "CrewAI execution produced no summary",
                metadata={"task_id": task.id, "suggestion_count": len(suggestions)},
            )

        except Exception as e:
            return AgentResponse(
                agent_id=self.agent_id,
                agent_name=self.config.name,
                suggestions=[],
                confidence=0.0,
                reasoning=f"Failed to parse CrewAI result: {str(e)}",
                metadata={"task_id": task.id, "error": str(e)},
            )

    def _parse_suggestions(self, result_text: str) -> List[Suggestion]:
        """
        Parse suggestions from CrewAI result text

        Args:
            result_text: Result text from CrewAI

        Returns:
            List of suggestions
        """
        suggestions = []

        # Extract code blocks from result
        import re

        code_blocks = re.findall(r"```[\w]*\n(.*?)```", result_text, re.DOTALL)

        if code_blocks:
            for i, code in enumerate(code_blocks):
                # Extract description (text before code block)
                description_match = re.search(
                    r"([^\n]+)\n```", result_text[: result_text.find(code)]
                )
                description = (
                    description_match.group(1)
                    if description_match
                    else f"Suggestion {i+1}"
                )

                suggestions.append(
                    Suggestion(
                        id=AdapterUtils.generate_suggestion_id("crewai"),
                        code=code.strip(),
                        description=description.strip(),
                        confidence=AdapterUtils.map_confidence_score(0.8),
                        diff=None,
                        applicable_range=None,
                    )
                )
        else:
            # If no code blocks, treat entire result as suggestion
            suggestions.append(
                Suggestion(
                    id=AdapterUtils.generate_suggestion_id("crewai"),
                    code=result_text.strip(),
                    description="General documentation suggestion",
                    confidence=AdapterUtils.map_confidence_score(0.6),
                    diff=None,
                    applicable_range=None,
                )
            )

        return suggestions

    def _calculate_confidence(
        self, result_text: str, suggestions: List[Suggestion]
    ) -> float:
        """
        Calculate confidence score based on result quality

        Args:
            result_text: Result text
            suggestions: Parsed suggestions

        Returns:
            Confidence score (0.0 to 1.0)
        """
        confidence = 0.5  # Base confidence

        # Increase confidence if we have suggestions
        if suggestions:
            confidence += 0.2

        # Increase confidence if result is detailed
        if len(result_text) > 200:
            confidence += 0.1

        # Increase confidence if result has code blocks
        if "```" in result_text:
            confidence += 0.1

        # Increase confidence if result has reasoning
        if any(
            keyword in result_text.lower()
            for keyword in ["because", "reason", "analysis"]
        ):
            confidence += 0.1

        return min(confidence, 1.0)

    async def get_capabilities(self) -> List[Capability]:
        """Get adapter capabilities"""
        return self.config.capabilities

    async def health_check(self) -> bool:
        """Check if adapter is healthy"""
        if not self._dependencies_available:
            return False

        try:
            if not self.is_initialized:
                return False

            # Check if LLM is accessible
            if self.llm:
                # Simple test query
                llm = self.llm
                test_result = await asyncio.get_event_loop().run_in_executor(
                    None, lambda: llm("Test")
                )
                return test_result is not None

            return True

        except Exception:
            return False

    async def shutdown(self) -> None:
        """Shutdown adapter and cleanup resources"""
        self.llm = None
        self.doc_agent = None
        self.test_agent = None
        self.crew = None
        await super().shutdown()


class CrewAIDocAgent(CrewAIAdapter):
    """Specialized CrewAI adapter for documentation generation"""

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
    """Specialized CrewAI adapter for test generation"""

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
