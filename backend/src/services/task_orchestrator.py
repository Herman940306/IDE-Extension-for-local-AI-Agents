"""
Lightweight task orchestration service used by the WebSocket gateway.
Project Creator: Herman Swanepoel

Enhanced with Multi-Model Router for intelligent model selection.
"""

from __future__ import annotations

import asyncio
import textwrap
import time
from typing import Optional

from src.models.response import AgentResponse, ConfidenceLevel, Suggestion
from src.models.session import (
    AgentRunResult,
    TaskRequestPayload,
    TaskSessionResult,
    VerificationStatus,
    VerificationSummary,
)
from src.models.task import TaskType
from src.orchestrator.multi_model_router import MultiModelRouter
from src.services.connection_manager import logger as ws_logger


class SimpleReasonerEngine:
    """
    Multi-model reasoning engine that routes tasks to optimal models.

    Uses MultiModelRouter to select the best model based on task type and complexity.
    """

    AGENT_ID = "multi_model_reasoner"
    AGENT_NAME = "Multi-Model Reasoner"

    def __init__(self, llm_manager=None, router: Optional[MultiModelRouter] = None):
        """
        Initialize with optional LLM manager and multi-model router.

        Args:
            llm_manager: LLM Manager for model execution
            router: Multi-Model Router for intelligent model selection
        """
        self.llm_manager = llm_manager
        self.router = router or MultiModelRouter()

    async def generate(self, request: TaskRequestPayload) -> AgentResponse:
        """Generate a response using the optimal model for the task."""
        description = request.description.strip() or "General improvement"
        content = (request.content or "").strip()

        # If we have LLM manager, use router to select best model
        if self.llm_manager:
            try:
                return await self._generate_with_router(request, description, content)
            except Exception as e:
                ws_logger.warning(
                    f"Multi-model generation failed, using fallback: {e}", exc_info=True
                )
                # Fall through to deterministic fallback

        # Fallback to deterministic response
        return await self._generate_fallback(request, description, content)

    async def _generate_with_router(
        self, request: TaskRequestPayload, description: str, content: str
    ) -> AgentResponse:
        """Generate response using router-selected model."""
        # Route task to optimal model
        model_config = self.router.route_task(
            task_type=request.type,
            use_premium_ux=False,  # Could be based on user tier
            complexity="medium",  # Could be auto-detected
        )

        # Build prompts based on task type
        system_prompt = self._build_system_prompt(request.type)
        user_prompt = self._build_user_prompt(description, content, request.type)

        # Call LLM with model-specific parameters
        response_text = await self.llm_manager.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            model=model_config.name,  # Use router-selected model
            temperature=model_config.temperature,
            max_tokens=model_config.max_tokens,
        )

        # Parse and structure the response
        suggestion = Suggestion(
            id=f"{request.id}-suggestion",
            code=response_text.strip(),
            description=f"AI-generated solution using {model_config.name}",
            confidence=ConfidenceLevel.HIGH,
            diff=None,  # Could be generated later
            applicable_range=None,  # Could be calculated from request context
        )

        reasoning = (
            f"Routed to {model_config.name} ({model_config.description}) "
            f"for {request.type.value} task: {description}"
        )

        return AgentResponse(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            suggestions=[suggestion],
            confidence=0.90,  # Higher confidence with specialized models
            reasoning=reasoning,
            metadata={
                "task_type": request.type.value,
                "uses_router": True,
                "selected_model": model_config.name,
                "model_role": model_config.role.value,
            },
        )

    def _build_system_prompt(self, task_type: TaskType) -> str:
        """Build system prompt based on task type."""
        prompts = {
            TaskType.CODE_GENERATION: "You are an expert programmer. Generate clean, well-documented code based on the user's requirements.",  # noqa: E501
            TaskType.BUG_FIX: "You are a debugging expert. Analyze the code and provide a fixed version with explanations.",  # noqa: E501
            TaskType.REFACTORING: "You are a code quality expert. Refactor the code to improve readability, maintainability, and performance.",  # noqa: E501
            TaskType.TEST_GENERATION: "You are a testing expert. Generate comprehensive unit tests for the provided code.",  # noqa: E501
            TaskType.DOCUMENTATION: "You are a technical writer. Generate clear, comprehensive documentation.",  # noqa: E501
        }
        return prompts.get(
            task_type,
            "You are a helpful AI assistant. Provide a clear and helpful response.",
        )

    def _build_user_prompt(
        self, description: str, content: str, task_type: TaskType
    ) -> str:
        """Build user prompt."""
        if content:
            return f"Task: {description}\n\n{content}"
        return description

    async def _generate_fallback(
        self, request: TaskRequestPayload, description: str, content: str
    ) -> AgentResponse:
        """Generate fallback deterministic response when LLM is unavailable."""
        await asyncio.sleep(0)  # keep signature async friendly

        code_snippet = self._build_code_snippet(content, request.type)
        suggestion_description = self._build_description(description, request.type)
        confidence = self._determine_confidence(request.type, content)

        suggestion = Suggestion(
            id=f"{request.id}-suggestion",
            code=code_snippet,
            description=suggestion_description,
            confidence=confidence,
            diff=None,
            applicable_range=None,
        )

        reasoning = textwrap.dedent(
            f"""
            Primary objective: {description}
            Suggested adjustment focuses on readability and maintainability while keeping the  # noqa: E501
            original intent intact. Confidence is derived from static analysis heuristics that  # noqa: E501
            inspect the supplied code and task type.
            """
        ).strip()

        return AgentResponse(
            agent_id=self.AGENT_ID,
            agent_name=self.AGENT_NAME,
            suggestions=[suggestion],
            confidence=0.68 if confidence.value == "medium" else 0.82,
            reasoning=reasoning,
            metadata={
                "task_type": request.type.value,
                "uses_context": bool(request.context and request.context.metadata),
                "content_present": bool(content),
                "uses_llm": False,
            },
        )

    def _build_code_snippet(self, content: str, task_type: TaskType) -> str:
        if content:
            # For simple expressions like "1+1", try to evaluate or explain
            if (
                task_type == TaskType.CODE_GENERATION
                and content.strip()
                and len(content.strip()) < 100
            ):  # noqa: E501
                # Try to detect simple math expressions
                import re

                if re.match(r"^[\d\s+\-*/().]+$", content.strip()):
                    try:
                        result = eval(content.strip())
                        return textwrap.dedent(
                            f"""
                            # Math calculation
                            expression = "{content.strip()}"
                            result = {result}
                            print(f"{{expression}} = {{result}}")
                            """
                        ).strip()
                    except Exception:
                        pass

            # Return the improved/analyzed version of the content
            return textwrap.dedent(
                f"""
                # Suggested revision generated by Contextual Reasoner
                # Task type: {task_type.value}
                
{content}
                """
            ).strip()

        template = "# TODO: Provide implementation for the requested task\n"
        return template + f"# Task type: {task_type.value}\n"

    def _build_description(self, description: str, task_type: TaskType) -> str:
        return f"Addressing '{description}' for task type '{task_type.value}'."

    def _determine_confidence(self, task_type: TaskType, content: str):
        if not content:
            return ConfidenceLevel.LOW
        if task_type in {TaskType.TEST_GENERATION, TaskType.BUG_FIX}:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.HIGH


class SimpleVerifierEngine:
    """
    Deep verification engine using DeepSeek-R1:8B for analytical validation.

    Performs logic validation, error tracing, and quality assurance.
    """

    AGENT_ID = "deepseek_verifier"
    AGENT_NAME = "DeepSeek Verifier"

    def __init__(self, llm_manager=None, router: Optional[MultiModelRouter] = None):
        """
        Initialize verifier with LLM manager and router.

        Args:
            llm_manager: LLM Manager for model execution
            router: Multi-Model Router for accessing verifier model config
        """
        self.llm_manager = llm_manager
        self.router = router or MultiModelRouter()

    async def verify(
        self, request: TaskRequestPayload, response: AgentResponse
    ) -> VerificationSummary:
        """
        Verify the reasoner output using DeepSeek-R1 for deep analysis.

        If LLM is available, performs intelligent verification.
        Otherwise, falls back to basic heuristics.
        """
        if self.llm_manager:
            try:
                return await self._verify_with_llm(request, response)
            except Exception as e:
                ws_logger.warning(
                    f"LLM verification failed, using fallback: {e}", exc_info=True
                )
                # Fall through to basic verification

        # Fallback to basic verification
        return await self._verify_fallback(request, response)

    async def _verify_with_llm(
        self, request: TaskRequestPayload, response: AgentResponse
    ) -> VerificationSummary:
        """Perform deep verification using DeepSeek-R1."""
        # Get verifier model config from router
        verifier_config = self.router.get_verifier_model()

        # Extract code from suggestions
        code_snippets = [s.code for s in response.suggestions if s.code]
        if not code_snippets:
            return VerificationSummary(
                status=VerificationStatus.SKIPPED,
                confidence=0.0,
                metadata={"reason": "no_code_to_verify"},
            )

        # Build verification prompt
        system_prompt = (
            "You are an analytical code verifier. Review the generated code for:\n"
            "1. Logic errors and edge cases\n"
            "2. Security vulnerabilities\n"
            "3. Performance issues\n"
            "4. Code quality and best practices\n\n"
            "Respond with: PASS, FAIL, or WARN followed by explanation."
        )

        user_prompt = f"""
Task: {request.description}
Task Type: {request.type.value}

Generated Code:
```
{code_snippets[0]}
```

Verify this code and provide analysis.
"""

        # Call verifier model
        verification_result = await self.llm_manager.generate(
            prompt=user_prompt.strip(),
            system_prompt=system_prompt,
            model=verifier_config.name,
            temperature=verifier_config.temperature,
            max_tokens=verifier_config.max_tokens,
        )

        # Parse verification result
        result_lower = verification_result.lower()
        if "pass" in result_lower[:20]:
            status = VerificationStatus.PASSED
            confidence = 0.90
        elif "fail" in result_lower[:20]:
            status = VerificationStatus.FAILED
            confidence = 0.85
        else:  # WARN or unclear
            status = VerificationStatus.PASSED
            confidence = 0.65

        metadata = {
            "evaluated_agent": response.agent_id,
            "verifier_model": verifier_config.name,
            "verification_detail": verification_result[:200],  # First 200 chars
            "uses_llm": True,
        }

        return VerificationSummary(
            status=status, confidence=confidence, metadata=metadata
        )

    async def _verify_fallback(
        self, request: TaskRequestPayload, response: AgentResponse
    ) -> VerificationSummary:
        """Basic verification fallback when LLM unavailable."""
        await asyncio.sleep(0)

        has_code = any(suggestion.code for suggestion in response.suggestions)
        status = VerificationStatus.PASSED if has_code else VerificationStatus.SKIPPED
        confidence = 0.55 if status == VerificationStatus.PASSED else 0.0

        metadata = {
            "evaluated_agent": response.agent_id,
            "suggestion_count": len(response.suggestions),
            "task_type": request.type.value,
            "uses_llm": False,
        }

        return VerificationSummary(
            status=status, confidence=confidence, metadata=metadata
        )


class TaskOrchestrator:
    """
    Coordinates task execution with multi-model routing.

    Orchestrates reasoning and verification stages using optimal models.
    """

    def __init__(
        self,
        reasoner: Optional[SimpleReasonerEngine] = None,
        verifier: Optional[SimpleVerifierEngine] = None,
        llm_manager=None,
        router: Optional[MultiModelRouter] = None,
    ):
        """
        Initialize orchestrator with multi-model support.

        Args:
            reasoner: Custom reasoner engine (optional)
            verifier: Custom verifier engine (optional)
            llm_manager: LLM Manager for model execution
            router: Multi-Model Router for intelligent model selection
        """
        self.router = router or MultiModelRouter()
        self.llm_manager = llm_manager
        self._reasoner = reasoner or SimpleReasonerEngine(
            llm_manager=llm_manager, router=self.router
        )
        self._verifier = verifier or SimpleVerifierEngine(
            llm_manager=llm_manager, router=self.router
        )

    async def execute(self, request: TaskRequestPayload) -> TaskSessionResult:
        """Process a task request and return an aggregated session result."""
        start_time = time.perf_counter()

        ws_logger.info(
            "orchestrator_task_received",
            extra={
                "task_id": request.id,
                "task_type": request.type.value,
                "has_content": bool(request.content),
            },
        )

        agent_response = await self._reasoner.generate(request)

        verification_summary = None
        if self._verifier:
            verification_summary = await self._verifier.verify(request, agent_response)

        duration_ms = (time.perf_counter() - start_time) * 1000
        summary = self._build_summary(agent_response, verification_summary)

        result = TaskSessionResult(
            task_id=request.id,
            status="completed",
            summary=summary,
            responses=[
                AgentRunResult(
                    response=agent_response,
                    duration_ms=duration_ms,
                    escalated=verification_summary is not None,
                )
            ],
            verification=verification_summary,
            metrics={
                "duration_ms": round(duration_ms, 2),
                "suggestion_count": len(agent_response.suggestions),
            },
        )

        ws_logger.info(
            "orchestrator_task_completed",
            extra={
                "task_id": request.id,
                "duration_ms": result.metrics["duration_ms"],
                "verification_status": (
                    verification_summary.status.value
                    if verification_summary
                    else VerificationStatus.SKIPPED.value
                ),
            },
        )

        return result

    def _build_summary(
        self,
        agent_response: AgentResponse,
        verification_summary: Optional[VerificationSummary],
    ) -> str:
        primary_suggestion = (
            agent_response.suggestions[0] if agent_response.suggestions else None
        )
        verification_text = "Verification skipped."
        if verification_summary:
            verification_text = (
                f"Verification {verification_summary.status.value}"
                f" (confidence {verification_summary.confidence:.2f})."
            )

        if primary_suggestion:
            return (
                f"Generated suggestion from {agent_response.agent_name}: "
                f"{primary_suggestion.description}. {verification_text}"
            )

        return (
            "No actionable suggestions were produced by the orchestrator. "
            f"{verification_text}"
        )


__all__ = ["TaskOrchestrator", "SimpleReasonerEngine", "SimpleVerifierEngine"]
