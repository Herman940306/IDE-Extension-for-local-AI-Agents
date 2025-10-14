"""
SuperAGI adapter for autonomous task execution
Project Creator: Herman Swanepoel
"""

import asyncio
from typing import Any, Dict, List, Optional

import httpx

from src.adapters.adapter_utils import AdapterExceptions, AdapterUtils
from src.adapters.base_adapter import AgentAdapter, AgentConfig, Capability
from src.models import AgentResponse, CodeContext, Suggestion, Task


class SuperAGIAdapter(AgentAdapter):
    """
    Adapter for SuperAGI framework

    Enables autonomous goal-driven execution with tool integration.
    SuperAGI agents can use various tools to accomplish complex tasks.
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize SuperAGI adapter

        Args:
            config: Agent configuration
        """
        super().__init__(config)
        self.base_url = config.metadata.get("superagi_url", "http://localhost:8001")
        self.api_key = config.metadata.get("api_key")
        self.agent_id: Optional[str] = None
        self.http_client: Optional[httpx.AsyncClient] = None

    async def initialize(self) -> None:
        """Initialize SuperAGI adapter and provision agent"""
        try:
            # Create HTTP client
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self.http_client = httpx.AsyncClient(
                base_url=self.base_url, headers=headers, timeout=30.0
            )

            # Provision agent
            agent_config = {
                "name": self.config.name,
                "description": self.config.description,
                "goals": self._get_default_goals(),
                "tools": self._get_tools(),
                "model": self.config.metadata.get("model", "gpt-3.5-turbo"),
                "max_iterations": self.config.metadata.get("max_iterations", 10),
            }

            response = await self.http_client.post("/agents", json=agent_config)
            response.raise_for_status()

            result = response.json()
            self.agent_id = result.get("agent_id")

            self.is_initialized = True

        except httpx.HTTPError as e:
            raise AdapterExceptions.AdapterConnectionError(f"Failed to connect to SuperAGI: {e}")
        except Exception as e:
            raise AdapterExceptions.AdapterInitializationError(
                f"Failed to initialize SuperAGI adapter: {e}"
            )

    async def execute_task(self, task: Task, context: CodeContext) -> AgentResponse:
        """
        Execute a task using SuperAGI agent

        Args:
            task: Task to execute
            context: Code context

        Returns:
            AgentResponse with suggestions
        """
        if not self.is_initialized:
            await self.initialize()

        try:
            # Extract goal from task
            goal = self._extract_goal(task, context)

            # Create execution request
            execution_request = {
                "agent_id": self.agent_id,
                "goal": goal,
                "context": {
                    "file_path": context.file_path,
                    "language": context.language,
                    "code": context.code,
                    "selected_text": context.selected_text,
                },
                "max_iterations": self.config.metadata.get("max_iterations", 10),
                "autonomous": True,
            }

            # Start execution
            response = await self.http_client.post("/executions", json=execution_request)
            response.raise_for_status()

            execution_result = response.json()
            execution_id = execution_result.get("execution_id")

            # Monitor execution progress
            result = await self._monitor_execution(execution_id)

            # Convert result to response
            return self._convert_result(result, task)

        except AdapterExceptions.AdapterError as e:
            return AgentResponse(
                task_id=task.id,
                agent_name=self.config.name,
                suggestions=[],
                confidence=0.0,
                reasoning=f"Task execution failed: {str(e)}",
            )
        except Exception as e:
            return AgentResponse(
                task_id=task.id,
                agent_name=self.config.name,
                suggestions=[],
                confidence=0.0,
                reasoning=f"Unexpected error: {str(e)}",
            )

    def _get_default_goals(self) -> List[str]:
        """Get default goals for the agent"""
        goals: List[str] = []

        if Capability.CODE_GENERATION in self.config.capabilities:
            goals.append("Generate high-quality, maintainable code")

        if Capability.REFACTORING in self.config.capabilities:
            goals.append("Improve code quality and maintainability")

        if Capability.BUG_DETECTION in self.config.capabilities:
            goals.append("Identify and fix bugs and security issues")

        if Capability.TESTING in self.config.capabilities:
            goals.append("Create comprehensive test coverage")

        return goals or ["Accomplish the given task efficiently"]

    def _get_tools(self) -> List[str]:
        """Get tools for the agent based on capabilities"""
        tools: List[str] = ["code_analysis", "file_reader", "file_writer", "web_search"]

        if Capability.CODE_GENERATION in self.config.capabilities:
            tools.extend(["code_generator", "syntax_checker"])

        if Capability.REFACTORING in self.config.capabilities:
            tools.extend(["refactoring_tool", "code_formatter"])

        if Capability.BUG_DETECTION in self.config.capabilities:
            tools.extend(["linter", "security_scanner"])

        if Capability.TESTING in self.config.capabilities:
            tools.extend(["test_generator", "test_runner"])

        return tools

    def _extract_goal(self, task: Task, context: CodeContext) -> str:
        """
        Extract goal from task

        Args:
            task: Task to execute
            context: Code context

        Returns:
            Goal string for SuperAGI
        """
        goal = f"Task: {task.type.value}\n"
        goal += f"Priority: {task.priority.value}\n\n"
        goal += f"Description: {task.description}\n\n"
        goal += f"File: {context.file_path}\n"
        goal += f"Language: {context.language}\n\n"

        if context.selected_text:
            goal += f"Focus on this code:\n```{context.language}\n{context.selected_text}\n```\n\n"

        goal += "Provide actionable suggestions with code examples."

        return goal

    async def _monitor_execution(self, execution_id: str) -> Dict[str, Any]:
        """
        Monitor execution progress with exponential backoff

        Args:
            execution_id: Execution ID to monitor

        Returns:
            Execution result
        """
        max_wait: int = self.config.timeout
        poll_interval: float = 2.0  # Initial interval in seconds
        max_interval: float = 10.0  # Cap at 10 seconds
        backoff_multiplier: float = 1.5
        elapsed: float = 0.0

        while elapsed < max_wait:
            try:
                response = await self.http_client.get(f"/executions/{execution_id}")
                response.raise_for_status()

                result = response.json()
                status = result.get("status")

                if status == "completed":
                    return result
                elif status == "failed":
                    raise Exception(f"Execution failed: {result.get('error')}")
                elif status == "cancelled":
                    raise Exception("Execution was cancelled")

                # Wait before next poll with exponential backoff
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

                # Increase interval with exponential backoff, capped at max_interval
                poll_interval = min(poll_interval * backoff_multiplier, max_interval)

            except httpx.HTTPError as e:
                raise AdapterExceptions.AdapterConnectionError(f"Failed to monitor execution: {e}")

        raise AdapterExceptions.AdapterTimeoutError(f"Execution timed out after {max_wait} seconds")

    def _convert_result(self, result: Dict[str, Any], task: Task) -> AgentResponse:
        """
        Convert SuperAGI result to our response format

        Args:
            result: SuperAGI execution result
            task: Original task

        Returns:
            AgentResponse
        """
        try:
            output = result.get("output", "")
            steps = result.get("steps", [])

            # Extract suggestions from output and steps
            suggestions = self._parse_suggestions(output, steps)

            # Calculate confidence based on execution success
            confidence = self._calculate_confidence(result, suggestions)

            # Build reasoning from steps
            reasoning = self._build_reasoning(steps, output)

            return AgentResponse(
                task_id=task.id,
                agent_name=self.config.name,
                suggestions=suggestions,
                confidence=confidence,
                reasoning=reasoning,
            )

        except Exception as e:
            return AgentResponse(
                task_id=task.id,
                agent_name=self.config.name,
                suggestions=[],
                confidence=0.0,
                reasoning=f"Failed to parse result: {str(e)}",
            )

    def _parse_suggestions(self, output: str, steps: List[Dict[str, Any]]) -> List[Suggestion]:
        """Parse suggestions from SuperAGI output using shared utilities"""
        suggestions: List[Suggestion] = []

        # Extract code blocks from output using shared utility
        code_blocks = AdapterUtils.extract_code_blocks(output)

        for code, description in code_blocks:
            suggestions.append(
                Suggestion(
                    code=code,
                    description=description,
                    confidence=0.85,
                    reasoning=f"Generated by {self.config.name} through autonomous execution",
                )
            )

        # Extract suggestions from steps
        for step in steps:
            if step.get("tool") == "code_generator":
                tool_output = step.get("output", "")
                if tool_output and "```" in tool_output:
                    step_blocks = AdapterUtils.extract_code_blocks(tool_output)
                    for code, _ in step_blocks:
                        suggestions.append(
                            Suggestion(
                                code=code,
                                description=step.get("thought", "Generated code"),
                                confidence=0.8,
                                reasoning=f"Step {step.get('step_number')}: {step.get('thought')}",
                            )
                        )

        return suggestions

    def _calculate_confidence(self, result: Dict[str, Any], suggestions: List[Suggestion]) -> float:
        """Calculate confidence score using shared utility"""
        steps = result.get("steps", [])
        success_rate = AdapterUtils.calculate_step_success_rate(steps)

        return AdapterUtils.calculate_base_confidence(
            status=result.get("status", "unknown"),
            has_suggestions=bool(suggestions),
            success_rate=success_rate,
        )

    def _build_reasoning(self, steps: List[Dict[str, Any]], output: str) -> str:
        """Build reasoning from execution steps using shared utility"""
        reasoning = "SuperAGI " + AdapterUtils.format_reasoning_steps(
            steps=steps, max_steps=5, step_key="thought"
        )

        reasoning += f"\nFinal Output:\n{AdapterUtils.truncate_output(output, 500)}"

        return reasoning

    async def get_capabilities(self) -> List[Capability]:
        """Get adapter capabilities"""
        return self.config.capabilities

    async def health_check(self) -> bool:
        """Check if adapter is healthy"""
        try:
            if not self.is_initialized or not self.http_client:
                return False

            # Check SuperAGI server health
            response = await self.http_client.get("/health")
            return response.status_code == 200

        except Exception:
            return False

    async def shutdown(self) -> None:
        """Shutdown adapter and cleanup resources"""
        try:
            # Delete agent if provisioned
            if self.agent_id and self.http_client:
                await self.http_client.delete(f"/agents/{self.agent_id}")

            # Close HTTP client
            if self.http_client:
                await self.http_client.aclose()

        except Exception as e:
            print(f"Error during shutdown: {e}")

        finally:
            self.http_client = None
            self.agent_id = None
            await super().shutdown()


class SuperAGICodeAgent(SuperAGIAdapter):
    """Specialized SuperAGI adapter for code generation"""

    def __init__(self):
        config = AgentConfig(
            name="SuperAGI Code Agent",
            description="Autonomous code generation using SuperAGI",
            capabilities=[Capability.CODE_GENERATION, Capability.REFACTORING],
            enabled=True,
            max_concurrent=1,
            timeout=120,
            metadata={
                "superagi_url": "http://localhost:8001",
                "model": "gpt-4",
                "max_iterations": 15,
            },
        )
        super().__init__(config)


class SuperAGIResearchAgent(SuperAGIAdapter):
    """Specialized SuperAGI adapter for research tasks"""

    def __init__(self):
        config = AgentConfig(
            name="SuperAGI Research Agent",
            description="Autonomous research and analysis using SuperAGI",
            capabilities=[Capability.RESEARCH, Capability.CODE_GENERATION],
            enabled=True,
            max_concurrent=1,
            timeout=180,
            metadata={
                "superagi_url": "http://localhost:8001",
                "model": "gpt-4",
                "max_iterations": 20,
            },
        )
        super().__init__(config)
