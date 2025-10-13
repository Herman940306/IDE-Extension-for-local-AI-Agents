"""
AutoGPT adapter for autonomous research and task execution
Project Creator: Herman Swanepoel
"""

import asyncio
import json
from typing import List, Dict, Any, Optional
import httpx

from src.adapters.base_adapter import AgentAdapter, AgentConfig, Capability
from src.models import Task, AgentResponse, Suggestion, CodeContext


class AutoGPTAdapter(AgentAdapter):
    """
    Adapter for AutoGPT framework
    
    Enables autonomous goal-driven execution with memory and plugin support.
    AutoGPT excels at research, planning, and complex multi-step tasks.
    """

    def __init__(self, config: AgentConfig):
        """
        Initialize AutoGPT adapter
        
        Args:
            config: Agent configuration
        """
        super().__init__(config)
        self.base_url = config.metadata.get("autogpt_url", "http://localhost:8002")
        self.api_key = config.metadata.get("api_key")
        self.agent_id: Optional[str] = None
        self.http_client: Optional[httpx.AsyncClient] = None
        self.workspace_path: Optional[str] = None

    async def initialize(self) -> None:
        """Initialize AutoGPT adapter and create agent"""
        try:
            # Create HTTP client
            headers = {}
            if self.api_key:
                headers["Authorization"] = f"Bearer {self.api_key}"

            self.http_client = httpx.AsyncClient(
                base_url=self.base_url,
                headers=headers,
                timeout=60.0
            )

            # Create agent
            agent_config = {
                "name": self.config.name,
                "role": self._get_role(),
                "goals": self._get_default_goals(),
                "plugins": self._get_plugins(),
                "model": self.config.metadata.get("model", "gpt-4"),
                "memory_backend": "local",
                "workspace": self.config.metadata.get("workspace", "autogpt_workspace")
            }

            response = await self.http_client.post("/agents", json=agent_config)
            response.raise_for_status()
            
            result = response.json()
            self.agent_id = result.get("agent_id")
            self.workspace_path = result.get("workspace_path")

            self.is_initialized = True

        except Exception as e:
            raise Exception(f"Failed to initialize AutoGPT adapter: {e}")

    async def execute_task(self, task: Task, context: CodeContext) -> AgentResponse:
        """
        Execute a task using AutoGPT agent
        
        Args:
            task: Task to execute
            context: Code context
            
        Returns:
            AgentResponse with suggestions
        """
        if not self.is_initialized:
            await self.initialize()

        try:
            # Prepare workspace with code context
            await self._prepare_workspace(context)

            # Create task for AutoGPT
            autogpt_task = {
                "agent_id": self.agent_id,
                "task": self._format_task(task, context),
                "context": {
                    "file_path": context.file_path,
                    "language": context.language,
                    "workspace": self.workspace_path
                },
                "continuous_mode": False,
                "continuous_limit": self.config.metadata.get("max_iterations", 10)
            }

            # Execute task
            response = await self.http_client.post(
                "/tasks",
                json=autogpt_task
            )
            response.raise_for_status()
            
            task_result = response.json()
            task_id = task_result.get("task_id")

            # Monitor task execution
            result = await self._monitor_task(task_id)

            # Convert result to response
            return self._convert_result(result, task, context)

        except Exception as e:
            return AgentResponse(
                task_id=task.id,
                agent_name=self.config.name,
                suggestions=[],
                confidence=0.0,
                reasoning=f"Task execution failed: {str(e)}"
            )

    def _get_role(self) -> str:
        """Get agent role based on capabilities"""
        if Capability.RESEARCH in self.config.capabilities:
            return "Research and Analysis Specialist"
        elif Capability.CODE_GENERATION in self.config.capabilities:
            return "Software Development Expert"
        elif Capability.BUG_DETECTION in self.config.capabilities:
            return "Code Quality and Security Analyst"
        else:
            return "General Purpose AI Assistant"

    def _get_default_goals(self) -> List[str]:
        """Get default goals for the agent"""
        goals = []

        if Capability.RESEARCH in self.config.capabilities:
            goals.extend([
                "Research and gather comprehensive information",
                "Analyze findings and provide insights",
                "Document research with sources"
            ])
        
        if Capability.CODE_GENERATION in self.config.capabilities:
            goals.extend([
                "Generate high-quality, maintainable code",
                "Follow best practices and design patterns",
                "Provide clear explanations"
            ])
        
        if Capability.BUG_DETECTION in self.config.capabilities:
            goals.extend([
                "Identify bugs and security vulnerabilities",
                "Suggest fixes with explanations",
                "Prioritize issues by severity"
            ])

        return goals or ["Accomplish the given task efficiently and thoroughly"]

    def _get_plugins(self) -> List[str]:
        """Get plugins for the agent"""
        plugins = [
            "file_operations",
            "web_search",
            "code_analysis"
        ]

        if Capability.RESEARCH in self.config.capabilities:
            plugins.extend([
                "web_scraper",
                "wikipedia",
                "arxiv"
            ])
        
        if Capability.CODE_GENERATION in self.config.capabilities:
            plugins.extend([
                "code_executor",
                "syntax_checker",
                "formatter"
            ])

        return plugins

    async def _prepare_workspace(self, context: CodeContext) -> None:
        """
        Prepare workspace with code context
        
        Args:
            context: Code context to add to workspace
        """
        try:
            if not self.workspace_path:
                return

            # Write code to workspace file
            workspace_data = {
                "agent_id": self.agent_id,
                "file_path": context.file_path,
                "content": context.code,
                "language": context.language
            }

            await self.http_client.post(
                "/workspace/files",
                json=workspace_data
            )

        except Exception as e:
            print(f"Failed to prepare workspace: {e}")

    def _format_task(self, task: Task, context: CodeContext) -> str:
        """
        Format task for AutoGPT
        
        Args:
            task: Task to format
            context: Code context
            
        Returns:
            Formatted task string
        """
        formatted = f"Task Type: {task.type.value}\n"
        formatted += f"Priority: {task.priority.value}\n\n"
        formatted += f"Description:\n{task.description}\n\n"
        formatted += f"Context:\n"
        formatted += f"- File: {context.file_path}\n"
        formatted += f"- Language: {context.language}\n\n"
        
        if context.selected_text:
            formatted += f"Focus Area:\n```{context.language}\n{context.selected_text}\n```\n\n"
        
        formatted += "Requirements:\n"
        formatted += "1. Analyze the code thoroughly\n"
        formatted += "2. Provide specific, actionable suggestions\n"
        formatted += "3. Include code examples where applicable\n"
        formatted += "4. Explain your reasoning\n"

        return formatted

    async def _monitor_task(self, task_id: str) -> Dict[str, Any]:
        """
        Monitor task execution
        
        Args:
            task_id: Task ID to monitor
            
        Returns:
            Task result
        """
        max_wait = self.config.timeout
        poll_interval = 3  # seconds
        elapsed = 0

        while elapsed < max_wait:
            try:
                response = await self.http_client.get(f"/tasks/{task_id}")
                response.raise_for_status()
                
                result = response.json()
                status = result.get("status")

                if status == "completed":
                    return result
                elif status == "failed":
                    raise Exception(f"Task failed: {result.get('error')}")
                elif status == "user_input_required":
                    # Auto-respond to continue execution
                    await self._provide_input(task_id, "Continue with the task")
                
                # Wait before next poll
                await asyncio.sleep(poll_interval)
                elapsed += poll_interval

            except httpx.HTTPError as e:
                raise Exception(f"Failed to monitor task: {e}")

        raise Exception(f"Task timed out after {max_wait} seconds")

    async def _provide_input(self, task_id: str, input_text: str) -> None:
        """Provide input to AutoGPT when requested"""
        try:
            await self.http_client.post(
                f"/tasks/{task_id}/input",
                json={"input": input_text}
            )
        except Exception as e:
            print(f"Failed to provide input: {e}")

    def _convert_result(
        self, 
        result: Dict[str, Any], 
        task: Task,
        context: CodeContext
    ) -> AgentResponse:
        """
        Convert AutoGPT result to our response format
        
        Args:
            result: AutoGPT task result
            task: Original task
            context: Code context
            
        Returns:
            AgentResponse
        """
        try:
            output = result.get("output", "")
            thoughts = result.get("thoughts", [])
            actions = result.get("actions", [])
            
            # Extract suggestions
            suggestions = self._parse_suggestions(output, actions, context)
            
            # Calculate confidence
            confidence = self._calculate_confidence(result, suggestions)

            # Build reasoning
            reasoning = self._build_reasoning(thoughts, actions, output)

            return AgentResponse(
                task_id=task.id,
                agent_name=self.config.name,
                suggestions=suggestions,
                confidence=confidence,
                reasoning=reasoning
            )

        except Exception as e:
            return AgentResponse(
                task_id=task.id,
                agent_name=self.config.name,
                suggestions=[],
                confidence=0.0,
                reasoning=f"Failed to parse result: {str(e)}"
            )

    def _parse_suggestions(
        self, 
        output: str, 
        actions: List[Dict[str, Any]],
        context: CodeContext
    ) -> List[Suggestion]:
        """Parse suggestions from AutoGPT output"""
        suggestions = []

        # Extract code blocks from output
        import re
        code_blocks = re.findall(r'```[\w]*\n(.*?)```', output, re.DOTALL)

        if code_blocks:
            for i, code in enumerate(code_blocks):
                # Find description
                description_match = re.search(
                    r'([^\n]+)\n```',
                    output[:output.find(code)]
                )
                description = description_match.group(1) if description_match else f"Suggestion {i+1}"

                suggestions.append(Suggestion(
                    code=code.strip(),
                    description=description.strip(),
                    confidence=0.85,
                    reasoning=f"Generated by {self.config.name} through autonomous research and analysis"
                ))

        # Extract suggestions from file operations
        for action in actions:
            if action.get("name") == "write_file":
                file_content = action.get("args", {}).get("content", "")
                if file_content:
                    suggestions.append(Suggestion(
                        code=file_content,
                        description=f"Generated file: {action.get('args', {}).get('filename', 'output')}",
                        confidence=0.8,
                        reasoning=action.get("reasoning", "File generated by AutoGPT")
                    ))

        return suggestions

    def _calculate_confidence(
        self, 
        result: Dict[str, Any], 
        suggestions: List[Suggestion]
    ) -> float:
        """Calculate confidence score"""
        confidence = 0.5  # Base confidence

        # Increase if task completed
        if result.get("status") == "completed":
            confidence += 0.2

        # Increase if we have suggestions
        if suggestions:
            confidence += 0.2

        # Increase based on number of thoughts (indicates thorough analysis)
        thoughts = result.get("thoughts", [])
        if len(thoughts) > 5:
            confidence += 0.1

        return min(confidence, 1.0)

    def _build_reasoning(
        self, 
        thoughts: List[Dict[str, Any]], 
        actions: List[Dict[str, Any]],
        output: str
    ) -> str:
        """Build reasoning from AutoGPT execution"""
        reasoning = f"AutoGPT Analysis:\n\n"

        # Add key thoughts
        if thoughts:
            reasoning += "Key Thoughts:\n"
            for i, thought in enumerate(thoughts[:5], 1):
                text = thought.get("text", "")
                reasoning += f"{i}. {text}\n"
            
            if len(thoughts) > 5:
                reasoning += f"... and {len(thoughts) - 5} more thoughts\n"
            reasoning += "\n"

        # Add actions taken
        if actions:
            reasoning += "Actions Taken:\n"
            for i, action in enumerate(actions[:5], 1):
                name = action.get("name", "unknown")
                reasoning += f"{i}. {name}\n"
                if action.get("reasoning"):
                    reasoning += f"   Reason: {action['reasoning']}\n"
            
            if len(actions) > 5:
                reasoning += f"... and {len(actions) - 5} more actions\n"
            reasoning += "\n"

        # Add output summary
        reasoning += f"Output:\n{output[:500]}"
        if len(output) > 500:
            reasoning += "..."

        return reasoning

    async def get_capabilities(self) -> List[Capability]:
        """Get adapter capabilities"""
        return self.config.capabilities

    async def health_check(self) -> bool:
        """Check if adapter is healthy"""
        try:
            if not self.is_initialized or not self.http_client:
                return False

            # Check AutoGPT server health
            response = await self.http_client.get("/health")
            return response.status_code == 200

        except Exception:
            return False

    async def shutdown(self) -> None:
        """Shutdown adapter and cleanup resources"""
        try:
            # Delete agent if created
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
            self.workspace_path = None
            await super().shutdown()


class AutoGPTResearchAgent(AutoGPTAdapter):
    """Specialized AutoGPT adapter for research tasks"""

    def __init__(self):
        config = AgentConfig(
            name="AutoGPT Research Agent",
            description="Autonomous research and analysis using AutoGPT",
            capabilities=[
                Capability.RESEARCH,
                Capability.CODE_GENERATION
            ],
            enabled=True,
            max_concurrent=1,
            timeout=180,
            metadata={
                "autogpt_url": "http://localhost:8002",
                "model": "gpt-4",
                "max_iterations": 25,
                "workspace": "research_workspace"
            }
        )
        super().__init__(config)


class AutoGPTCodeAnalysisAgent(AutoGPTAdapter):
    """Specialized AutoGPT adapter for code analysis"""

    def __init__(self):
        config = AgentConfig(
            name="AutoGPT Code Analysis Agent",
            description="Deep code analysis using AutoGPT",
            capabilities=[
                Capability.BUG_DETECTION,
                Capability.REFACTORING,
                Capability.CODE_GENERATION
            ],
            enabled=True,
            max_concurrent=1,
            timeout=120,
            metadata={
                "autogpt_url": "http://localhost:8002",
                "model": "gpt-4",
                "max_iterations": 15,
                "workspace": "code_analysis_workspace"
            }
        )
        super().__init__(config)
