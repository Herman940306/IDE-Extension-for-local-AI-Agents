"""
Reasoning Coordinator - Dual-Process Integration (System 1 + System 2)
Project Creator: Herman Swanepoel

Implements the coordination layer between:
- System 1 (Fast Reasoner): LLaMA 3.2 3B for rapid intuitive responses
- System 2 (Analytical Verifier): Mistral 7B for thorough verification

Follows Kahneman's dual-process theory with adaptive routing based on
task complexity and confidence thresholds.
"""

import logging
import time
from enum import Enum
from typing import Any, Dict, List, Optional

from ..models.reasoner import FastReasoner, ReasoningRequest
from ..models.verifier import (
    AnalyticalVerifier,
    VerificationRequest,
)
from .meta_controller import MetaController
from .task_router import TaskRouter

logger = logging.getLogger(__name__)


class ProcessingMode(str, Enum):
    """Processing mode selection"""

    SYSTEM1_ONLY = "system1_only"  # Fast path
    SYSTEM2_ONLY = "system2_only"  # Analytical path
    DUAL_PROCESS = "dual_process"  # Both systems
    ADAPTIVE = "adaptive"  # Dynamic selection


class ReasoningResult(Dict[str, Any]):
    """Result from reasoning coordinator"""


class ReasoningCoordinator:
    """
    Coordinates dual-process reasoning between System 1 and System 2.

    Implements adaptive routing strategy:
    - Simple tasks → System 1 only (fast path)
    - Complex tasks → System 1 + System 2 (verification)
    - Low confidence → Escalate to System 2
    - High confidence + simple → Skip System 2
    """

    def __init__(
        self,
        reasoner: FastReasoner,
        verifier: AnalyticalVerifier,
        task_router: TaskRouter,
        meta_controller: MetaController,
        confidence_threshold: float = 0.75,
        complexity_threshold: float = 0.5,
    ):
        """
        Initialize reasoning coordinator.

        Args:
            reasoner: System 1 fast reasoner
            verifier: System 2 analytical verifier
            task_router: Task routing component
            meta_controller: Meta-controller for orchestration
            confidence_threshold: Threshold for System 2 escalation
            complexity_threshold: Threshold for dual-process mode
        """
        self.reasoner = reasoner
        self.verifier = verifier
        self.task_router = task_router
        self.meta_controller = meta_controller
        self.confidence_threshold = confidence_threshold
        self.complexity_threshold = complexity_threshold

        # Performance tracking
        self.total_requests = 0
        self.system1_only_count = 0
        self.dual_process_count = 0
        self.escalations = 0

        logger.info(
            f"ReasoningCoordinator initialized: "
            f"conf_threshold={confidence_threshold}, "
            f"complexity_threshold={complexity_threshold}"
        )

    async def process(
        self,
        task_type: str,
        description: str,
        code_context: str,
        language: str,
        selected_text: Optional[str] = None,
        mode: ProcessingMode = ProcessingMode.ADAPTIVE,
    ) -> ReasoningResult:
        """
        Process a reasoning request using dual-process coordination.

        Args:
            task_type: Type of task (refactor, explain, etc.)
            description: Task description
            code_context: Code context
            language: Programming language
            selected_text: Optional selected code
            mode: Processing mode (adaptive by default)

        Returns:
            ReasoningResult with suggestions and metadata
        """
        start_time = time.time()
        self.total_requests += 1

        logger.info(f"Processing request: type={task_type}, mode={mode.value}")

        try:
            # Analyze task
            task_analysis = self.task_router.analyze_task(description, code_context, language)

            complexity = task_analysis["complexity"]
            intent = task_analysis["intent"]

            # Determine processing strategy
            strategy = self._determine_strategy(mode, complexity, task_analysis)

            logger.info(f"Strategy: {strategy}, complexity={complexity:.2f}, intent={intent}")

            # Execute based on strategy
            if strategy == ProcessingMode.SYSTEM1_ONLY:
                result = await self._process_system1_only(
                    task_type, description, code_context, language, selected_text
                )
                self.system1_only_count += 1

            elif strategy == ProcessingMode.DUAL_PROCESS:
                result = await self._process_dual_system(
                    task_type, description, code_context, language, selected_text
                )
                self.dual_process_count += 1

            else:  # ADAPTIVE
                result = await self._process_adaptive(
                    task_type, description, code_context, language, selected_text, complexity
                )

            # Add metadata
            total_latency = (time.time() - start_time) * 1000
            result["metadata"] = {
                "total_latency_ms": total_latency,
                "strategy": strategy.value,
                "complexity": complexity,
                "intent": intent,
                "task_analysis": task_analysis,
            }

            # Update meta-controller
            self._update_performance_metrics(result)

            logger.info(f"Request completed: {total_latency:.0f}ms, strategy={strategy.value}")

            return result

        except Exception as e:
            logger.error(f"Processing failed: {e}", exc_info=True)
            return ReasoningResult(
                {
                    "success": False,
                    "error": str(e),
                    "suggestions": [],
                    "metadata": {"total_latency_ms": (time.time() - start_time) * 1000},
                }
            )

    def _determine_strategy(
        self, mode: ProcessingMode, complexity: float, task_analysis: Dict[str, Any]
    ) -> ProcessingMode:
        """Determine processing strategy"""
        # If explicit mode specified (not ADAPTIVE), use it
        if mode != ProcessingMode.ADAPTIVE:
            return mode

        # For ADAPTIVE mode, return ADAPTIVE to let _process_adaptive decide
        # It will run System1 first and then decide whether to escalate
        return ProcessingMode.ADAPTIVE

    async def _process_system1_only(
        self,
        task_type: str,
        description: str,
        code_context: str,
        language: str,
        selected_text: Optional[str],
    ) -> ReasoningResult:
        """Process using System 1 only (fast path)"""
        logger.info("Executing System 1 only (fast path)")

        # System 1: Fast reasoning
        request = ReasoningRequest(
            task_type=task_type,
            description=description,
            code_context=code_context,
            language=language,
            selected_text=selected_text,
        )

        response = await self.reasoner.reason(request)

        return ReasoningResult(
            {
                "success": True,
                "suggestions": response.suggestions,
                "confidence": response.confidence,
                "reasoning": response.reasoning,
                "system1_response": response.dict(),
                "system2_response": None,
                "verification_skipped": True,
            }
        )

    async def _process_dual_system(
        self,
        task_type: str,
        description: str,
        code_context: str,
        language: str,
        selected_text: Optional[str],
    ) -> ReasoningResult:
        """Process using both System 1 and System 2"""
        logger.info("Executing dual-process (System 1 + System 2)")

        # System 1: Fast reasoning
        reasoning_request = ReasoningRequest(
            task_type=task_type,
            description=description,
            code_context=code_context,
            language=language,
            selected_text=selected_text,
        )

        system1_response = await self.reasoner.reason(reasoning_request)

        # System 2: Verification
        if system1_response.suggestions:
            verification_request = VerificationRequest(
                code=system1_response.suggestions[0],  # Verify first suggestion
                language=language,
                context=code_context,
                original_task=description,
                system1_confidence=system1_response.confidence,
            )

            system2_response = await self.verifier.verify(verification_request)

            # Combine results
            final_confidence = self._combine_confidence(
                system1_response.confidence, system2_response.confidence, system2_response.valid
            )

            # Merge suggestions
            final_suggestions = self._merge_suggestions(
                system1_response.suggestions, system2_response.suggestions, system2_response.valid
            )

            return ReasoningResult(
                {
                    "success": True,
                    "suggestions": final_suggestions,
                    "confidence": final_confidence,
                    "reasoning": f"System 1: {system1_response.reasoning}\nSystem 2: {system2_response.reasoning}",
                    "system1_response": system1_response.dict(),
                    "system2_response": system2_response.dict(),
                    "verification_passed": system2_response.valid,
                    "issues": system2_response.issues,
                }
            )
        else:
            # No suggestions from System 1
            return ReasoningResult(
                {
                    "success": False,
                    "suggestions": [],
                    "confidence": 0.0,
                    "reasoning": "System 1 produced no suggestions",
                    "system1_response": system1_response.dict(),
                    "system2_response": None,
                }
            )

    async def _process_adaptive(
        self,
        task_type: str,
        description: str,
        code_context: str,
        language: str,
        selected_text: Optional[str],
        complexity: float,
    ) -> ReasoningResult:
        """Process with adaptive strategy based on System 1 confidence"""
        logger.info("Executing adaptive strategy")

        # Always start with System 1
        reasoning_request = ReasoningRequest(
            task_type=task_type,
            description=description,
            code_context=code_context,
            language=language,
            selected_text=selected_text,
        )

        system1_response = await self.reasoner.reason(reasoning_request)

        # Decide whether to escalate to System 2
        should_verify = (
            system1_response.confidence < self.confidence_threshold
            or complexity > self.complexity_threshold
            or not system1_response.suggestions
        )

        if should_verify:
            logger.info(
                f"Escalating to System 2: "
                f"conf={system1_response.confidence:.2f}, "
                f"complexity={complexity:.2f}"
            )
            self.escalations += 1

            # Run System 2 verification
            return await self._process_dual_system(
                task_type, description, code_context, language, selected_text
            )
        else:
            logger.info(f"System 1 sufficient: conf={system1_response.confidence:.2f}")
            self.system1_only_count += 1

            return ReasoningResult(
                {
                    "success": True,
                    "suggestions": system1_response.suggestions,
                    "confidence": system1_response.confidence,
                    "reasoning": system1_response.reasoning,
                    "system1_response": system1_response.dict(),
                    "system2_response": None,
                    "verification_skipped": True,
                }
            )

    def _combine_confidence(
        self, system1_conf: float, system2_conf: float, verified: bool
    ) -> float:
        """Combine confidence scores from both systems"""
        if not verified:
            # Verification failed, lower confidence
            return min(system1_conf, system2_conf) * 0.7

        # Weighted average favoring System 2
        return system1_conf * 0.3 + system2_conf * 0.7

    def _merge_suggestions(
        self, system1_suggestions: List[str], system2_suggestions: List[str], verified: bool
    ) -> List[str]:
        """Merge suggestions from both systems"""
        if not verified:
            # Return System 2 suggestions if verification failed
            return system2_suggestions if system2_suggestions else system1_suggestions

        # Combine unique suggestions
        merged = system1_suggestions.copy()
        for suggestion in system2_suggestions:
            if suggestion not in merged:
                merged.append(suggestion)

        return merged

    def _update_performance_metrics(self, result: ReasoningResult) -> None:
        """Update meta-controller with performance metrics"""
        result.get("metadata", {})

        # Update for System 1
        if result.get("system1_response"):
            self.meta_controller.update_graph(
                {
                    "agent": "Reasoner",
                    "latency": result["system1_response"]["latency_ms"],
                    "success": result.get("success", False),
                    "confidence": result["system1_response"]["confidence"],
                }
            )

        # Update for System 2
        if result.get("system2_response"):
            self.meta_controller.update_graph(
                {
                    "agent": "Verifier",
                    "latency": result["system2_response"]["latency_ms"],
                    "success": result["system2_response"]["valid"],
                    "confidence": result["system2_response"]["confidence"],
                }
            )

    def get_stats(self) -> Dict[str, Any]:
        """Get coordinator statistics"""
        system1_rate = (
            self.system1_only_count / self.total_requests if self.total_requests > 0 else 0
        )

        dual_process_rate = (
            self.dual_process_count / self.total_requests if self.total_requests > 0 else 0
        )

        escalation_rate = self.escalations / self.total_requests if self.total_requests > 0 else 0

        return {
            "total_requests": self.total_requests,
            "system1_only_count": self.system1_only_count,
            "dual_process_count": self.dual_process_count,
            "escalations": self.escalations,
            "system1_rate": system1_rate,
            "dual_process_rate": dual_process_rate,
            "escalation_rate": escalation_rate,
            "system1_stats": self.reasoner.get_stats(),
            "system2_stats": self.verifier.get_stats(),
            "graph_state": self.meta_controller.get_graph_state(),
        }

    async def close(self):
        """Close all resources"""
        await self.reasoner.close()
        await self.verifier.close()
        logger.info("ReasoningCoordinator closed")
