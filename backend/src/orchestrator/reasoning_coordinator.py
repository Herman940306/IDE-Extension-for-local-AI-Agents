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

from ..config.settings import get_settings as get_app_settings
from ..models.reasoner import FastReasoner, ReasoningRequest
from ..models.verifier import (
    AnalyticalVerifier,
    VerificationRequest,
    VerificationResponse,
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

        # Lightweight in-memory LRU cache for System 2 / advanced results
        from collections import OrderedDict

        self._verify_cache: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
        self._verify_cache_max = 64

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
            task_analysis = self.task_router.analyze_task(
                description, code_context, language
            )

            complexity = task_analysis["complexity"]
            intent = task_analysis["intent"]

            # Optional UX pre-warm for explain tasks (non-blocking)
            try:
                if task_type.lower() == "explain":
                    await self._prewarm_model_async("gemma2:9b", keep_alive="5m")
            except Exception as _pw:
                logger.debug(f"UX prewarm skipped: {_pw}")

            # Determine processing strategy
            strategy = self._determine_strategy(mode, complexity, task_analysis)

            logger.info(
                f"Strategy: {strategy}, complexity={complexity:.2f}, intent={intent}"
            )

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
                    task_type,
                    description,
                    code_context,
                    language,
                    selected_text,
                    complexity,
                )

            # Optional safety check on merged output
            settings = get_app_settings()
            if getattr(settings, "enable_safety_check", False):
                try:
                    merged_text = "\n\n".join(result.get("suggestions", [])[:2])
                    safety = await self._run_safety_check(merged_text)
                    result["safety_check"] = safety
                except Exception as _e:
                    logger.debug(f"Safety check skipped/failed: {_e}")

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

            logger.info(
                f"Request completed: {total_latency:.0f}ms, strategy={strategy.value}"
            )

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

        # System 2: Verification (with optional advanced escalation)
        if system1_response.suggestions:
            verification_request = VerificationRequest(
                code=system1_response.suggestions[0],  # Verify first suggestion
                language=language,
                context=code_context,
                original_task=description,
                system1_confidence=system1_response.confidence,
            )
            # Decide if we should escalate to advanced model for deep reasoning
            settings = get_app_settings()
            use_advanced = self._should_use_advanced(
                description=description,
                code_context=code_context,
                system1_confidence=system1_response.confidence,
            )

            original_model = self.verifier.model
            if use_advanced:
                logger.info(
                    "Escalating to advanced reasoning model: %s",
                    getattr(settings, "advanced_model", "codellama:13b-instruct-q4_0"),
                )
                self.verifier.model = getattr(
                    settings, "advanced_model", "codellama:13b-instruct-q4_0"
                )

            try:
                # Check LRU cache first
                cache_key = self._make_verify_cache_key(
                    self.verifier.model, verification_request
                )
                cached = self._verify_cache_get(cache_key)
                if cached:
                    logger.info("Using cached System 2/advanced verification result")
                    system2_response = VerificationResponse(**cached)
                else:
                    system2_response = await self.verifier.verify(verification_request)
                    self._verify_cache_set(cache_key, system2_response.dict())
            finally:
                # Restore verifier model
                self.verifier.model = original_model

            # Combine results
            final_confidence = self._combine_confidence(
                system1_response.confidence,
                system2_response.confidence,
                system2_response.valid,
            )

            # Merge suggestions
            final_suggestions = self._merge_suggestions(
                system1_response.suggestions,
                system2_response.suggestions,
                system2_response.valid,
            )

            return ReasoningResult(
                {
                    "success": True,
                    "suggestions": final_suggestions,
                    "confidence": final_confidence,
                    "reasoning": f"System 1: {system1_response.reasoning}\nSystem 2: {system2_response.reasoning}",  # noqa: E501
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

    def _should_use_advanced(
        self,
        description: str,
        code_context: str,
        system1_confidence: float,
    ) -> bool:
        """Heuristic to determine if advanced 13B reasoning is warranted.

        Triggers on very high complexity signals: long contexts, low confidence,
        or explicit multi-file/deep refactor intents.
        """
        # Simple heuristics; can be replaced by a learned policy later
        too_long = code_context.count("\n") > 400 or len(code_context) > 20_000
        low_conf = system1_confidence < 0.55
        deep_keywords = [
            "multi-file",
            "deep refactor",
            "architectural",
            "cross-cutting",
            "comprehensive",
        ]
        mentions_deep = any(kw in description.lower() for kw in deep_keywords)
        return too_long or (low_conf and mentions_deep)

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

    async def _run_safety_check(self, text: str) -> Dict[str, Any]:
        """Run a lightweight safety check using the configured safety model."""
        import httpx

        settings = get_app_settings()
        if not text.strip():
            return {"status": "skipped", "reason": "empty_text"}

        payload = {
            "model": getattr(settings, "safety_model", "phi3:medium"),
            "prompt": (
                "You are a safety checker. Analyze the following output for sensitive "
                "information (credentials, API keys, secrets) or unsafe content. "
                'Reply ONLY with a JSON object {"flagged": bool, "notes": string}.'
                "\n\n"
                f"OUTPUT:\n{text}"
            ),
            "stream": False,
            "keep_alive": getattr(settings, "safety_keep_alive", "-1"),
            "options": {},
        }
        if getattr(settings, "safety_force_cpu", True):
            payload["options"]["num_gpu"] = 0

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.post(
                f"{get_app_settings().ollama_base_url}/api/generate", json=payload
            )
            resp.raise_for_status()
            data = resp.json()
            text_out = data.get("response", "").strip()

        # Best-effort parse of a JSON-like response
        import json

        try:
            # Extract JSON if wrapped
            start = text_out.find("{")
            end = text_out.rfind("}")
            if start != -1 and end != -1:
                parsed = json.loads(text_out[start : end + 1])
                return {"status": "ok", **parsed}
        except Exception:
            pass
        return {"status": "ok", "raw": text_out[:500]}

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
        self,
        system1_suggestions: List[str],
        system2_suggestions: List[str],
        verified: bool,
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

    def _make_verify_cache_key(self, model: str, req: VerificationRequest) -> str:
        """Key on model + essential request fields to identify repeats."""
        return (
            f"{model}|{req.language}|{len(req.code)}|{len(req.context)}|"
            f"{hash(req.original_task)}"
        )

    def _verify_cache_get(self, key: str) -> Optional[Dict[str, Any]]:
        try:
            val = self._verify_cache.pop(key)
            self._verify_cache[key] = val
            return val
        except KeyError:
            return None

    def _verify_cache_set(self, key: str, value: Dict[str, Any]) -> None:
        if key in self._verify_cache:
            self._verify_cache.pop(key)
        elif len(self._verify_cache) >= self._verify_cache_max:
            # Drop oldest
            self._verify_cache.popitem(last=False)
        self._verify_cache[key] = value

    async def _prewarm_model_async(self, model: str, keep_alive: str = "5m") -> None:
        """Fire-and-forget model pre-warm request to Ollama."""
        import httpx

        url = get_app_settings().ollama_base_url
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(
                    f"{url}/api/generate",
                    json={
                        "model": model,
                        "prompt": "warmup",
                        "stream": False,
                        "keep_alive": keep_alive,
                        "options": {"num_predict": 1},
                    },
                )
        except Exception:
            # Ignore prewarm errors silently
            pass

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
            self.system1_only_count / self.total_requests
            if self.total_requests > 0
            else 0
        )

        dual_process_rate = (
            self.dual_process_count / self.total_requests
            if self.total_requests > 0
            else 0
        )

        escalation_rate = (
            self.escalations / self.total_requests if self.total_requests > 0 else 0
        )

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
