"""
Lightweight task orchestration service used by the WebSocket gateway.
Project Creator: Herman Swanepoel

Enhanced with Multi-Model Router for intelligent model selection.
"""

from __future__ import annotations

import asyncio
import textwrap
import time
from collections import OrderedDict
from typing import Any, Dict, List, Optional, Tuple, cast

from src.config.settings import get_settings
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

# build_retriever_dict imported earlier; keep single import to avoid redefinition
from src.services.memory_service import MemoryService, get_memory_service
from src.services.retrieval.helpers import build_retriever_dict
from src.services.retrieval.trace import RetrievalDocTrace, retrieval_trace_buffer

settings = get_settings()


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
        self.router = router or MultiModelRouter(
            show_model_names=settings.show_model_names_in_responses
        )

    async def generate(self, request: TaskRequestPayload) -> AgentResponse:
        """Generate a response using the optimal model for the task."""
        description = request.description.strip() or "General improvement"
        content = (request.content or "").strip()

        # If we have LLM manager, use router to select best model
        if self.llm_manager:
            try:
                return await self._generate_with_router(
                    request, description, content
                )  # noqa: BLE001
            except Exception as e:  # noqa: BLE001
                ws_logger.warning(
                    "Multi-model generation failed, using fallback: %s",
                    e,
                    exc_info=True,
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

        # Build prompts based on task type (with adaptive personality for chat)
        system_prompt = self._build_system_prompt(request.type, description, content)
        user_prompt = self._build_user_prompt(description, content, request.type)

        # Call LLM with model-specific parameters
        llm = self.llm_manager
        assert llm is not None
        response_text = await llm.generate(
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
            description=(
                "AI-generated solution"
                if settings.clean_user_experience
                else f"AI-generated solution using {model_config.name}"
            ),
            confidence=ConfidenceLevel.HIGH,
            diff=None,  # Could be generated later
            applicable_range=None,  # Could be calculated from request context
        )

        # Build reasoning (hide model details if clean UX enabled)
        if settings.clean_user_experience:
            reasoning = f"Generated {request.type.value} solution: {description}"
        else:
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

    def _detect_user_mood(self, description: str, content: str) -> dict:
        """
        Detect user's emotional state from language patterns.

        Returns dict with:
        - mood: frustrated/stressed/happy/neutral/excited
        - intensity: 1-10 (how strong the emotion is)
        - needs_support: bool (requires empathetic response)
        """
        user_text = f"{description} {content}".strip().lower()

        # Frustration indicators
        frustrated_markers = [
            "doesn't work",
            "not working",
            "broken",
            "fails",
            "error",
            "wrong",
            "stuck",
            "help!",
            "frustrated",
            "wtf",
            "damn",
            "ugh",
            "argh",
            "why won't",
            "keeps failing",
            "still not",
            "tried everything",
        ]

        # Stress indicators
        stressed_markers = [
            "urgent",
            "asap",
            "deadline",
            "quickly",
            "hurry",
            "rush",
            "critical",
            "important",
            "need this now",
            "running out of time",
        ]

        # Happy/positive indicators
        happy_markers = [
            "thanks",
            "thank you",
            "awesome",
            "great",
            "love",
            "perfect",
            "amazing",
            "excellent",
            "appreciate",
            "helpful",
            "cool",
            "nice",
        ]

        # Excited/eager indicators
        excited_markers = [
            "excited",
            "can't wait",
            "eager",
            "looking forward",
            "awesome",
            "finally",
            "yes!",
            "wow",
            "fantastic",
        ]

        # Count emotional markers
        frustrated_count = sum(1 for m in frustrated_markers if m in user_text)
        stressed_count = sum(1 for m in stressed_markers if m in user_text)
        happy_count = sum(1 for m in happy_markers if m in user_text)
        excited_count = sum(1 for m in excited_markers if m in user_text)

        # Determine primary mood
        if frustrated_count > 0:
            mood = "frustrated"
            intensity = min(10, frustrated_count * 3)
            needs_support = True
        elif stressed_count > 0:
            mood = "stressed"
            intensity = min(10, stressed_count * 3)
            needs_support = True
        elif happy_count > 0:
            mood = "happy"
            intensity = min(10, happy_count * 2)
            needs_support = False
        elif excited_count > 0:
            mood = "excited"
            intensity = min(10, excited_count * 2)
            needs_support = False
        else:
            mood = "neutral"
            intensity = 5
            needs_support = False

        return {
            "mood": mood,
            "intensity": intensity,
            "needs_support": needs_support,
        }

    def _analyze_user_style(self, description: str, content: str) -> dict:
        """
        Analyze user's communication style to adapt response personality.

        Returns dict with style metrics (1-10 scale):
        - brevity: How concise the user is
        - formality: Professional vs casual tone
        - detail_level: Depth of explanation needed
        - mood: User's emotional state
        - needs_support: Requires empathetic response
        """
        user_text = f"{description} {content}".strip()
        word_count = len(user_text.split())

        # Brevity: Shorter prompts = concise responses
        brevity = 10 if word_count < 10 else (7 if word_count < 30 else 4)

        # Formality: Check for casual markers
        casual_markers = ["hi", "hey", "yo", "what's", "gonna", "wanna", "lol"]
        formal_markers = ["please", "kindly", "could you", "would you", "regarding"]

        casual_count = sum(1 for marker in casual_markers if marker in user_text.lower())
        formal_count = sum(1 for marker in formal_markers if marker in user_text.lower())

        if formal_count > casual_count:
            formality = 8  # Professional
        elif casual_count > 0:
            formality = 3  # Casual
        else:
            formality = 5  # Neutral

        # Detail level: More content = detailed response expected
        detail_level = 3 if word_count < 10 else (6 if word_count < 50 else 8)

        # Emoji preference cues
        contains_emoji = any(ch in user_text for ch in "😀😁😂🤣😊😍🙌👍🔥✨🥲😅😉🤔🙏🎉🚀💡")
        explicit_no_emoji = "no emoji" in user_text.lower() or "no emojis" in user_text.lower()
        exclamations = user_text.count("!")

        # Mood detection
        mood_info = self._detect_user_mood(description, content)

        return {
            "brevity": brevity,
            "formality": formality,
            "detail_level": detail_level,
            "mood": mood_info["mood"],
            "mood_intensity": mood_info["intensity"],
            "needs_support": mood_info["needs_support"],
            "contains_emoji": contains_emoji,
            "explicit_no_emoji": explicit_no_emoji,
            "exclamations": exclamations,
        }

    def _emoji_policy(self, user_style: dict) -> dict:
        """
        Decide whether and how many emojis to use, based on settings and user style.

        Returns:
            {
              "allow": bool,
              "max": int,
              "tone": "minimal"|"balanced"|"rich",
            }
        """
        allow = getattr(settings, "emoji_enabled_default", True)
        if user_style.get("explicit_no_emoji", False):
            allow = False

        # Reduce emoji usage in formal contexts
        formality = user_style.get("formality", 5)
        mood = user_style.get("mood", "neutral")
        intensity = int(user_style.get("mood_intensity", 5))
        has_user_emoji = user_style.get("contains_emoji", False)

        style_pref = getattr(settings, "emoji_style_default", "auto")
        base_max = int(getattr(settings, "emoji_max_per_response", 3))

        # Compute max count
        if not allow:
            max_count = 0
        else:
            if style_pref == "minimal" or formality >= 7:
                max_count = 0 if formality >= 8 else 1
            elif style_pref == "rich" or (has_user_emoji and formality <= 4):
                max_count = min(base_max + 1, 5)
            else:
                # auto: adapt to mood
                if mood in ("happy", "excited"):
                    max_count = min(base_max, 3)
                elif mood in ("frustrated", "stressed"):
                    # Keep gentle, avoid excess
                    max_count = 1 if intensity >= 7 else 0
                else:
                    max_count = min(base_max, 2)

        tone = "minimal" if max_count == 0 else ("balanced" if max_count <= 2 else "rich")

        return {"allow": allow, "max": max_count, "tone": tone}

    def _build_adaptive_chat_prompt(self, user_style: dict) -> str:
        """
        Build chat mode prompt with adaptive personality.

        Base Personality Traits (1-10 scale):
        - Warmth: 8 (empathetic, supportive)
        - Clarity: 9 (concise, structured)
        - Wit: 5 (light, situational)
        - Humor: 3 (gentle, non-sarcastic)
        - Humility: 7 (own mistakes, offer corrections)
        - Patience: 8 (pace with the user)
        - Encouragement: 8 (cheer progress, reduce friction)
        - Proactivity: 7 (offer next steps)
        - Collaboration: 9 (pair-programmer energy)

        Adapts to user style:
        - Short prompts → Brief, punchy responses
        - Detailed prompts → Thorough explanations
        - Casual tone → Relaxed, friendly
        - Formal tone → Professional, precise
        - Frustrated → Supportive, solution-focused
        - Stressed → Calm, efficient
        - Happy → Enthusiastic, engaging
        """
        brevity = user_style["brevity"]
        formality = user_style["formality"]
        detail_level = user_style["detail_level"]
        mood = user_style.get("mood", "neutral")
        # Whether user needs extra support is reflected in mood instruction
        # (value not directly used here to avoid verbosity)
        _ = user_style.get("needs_support", False)
        emoji_cfg = self._emoji_policy(user_style)

        # Build adaptive personality instructions
        tone = (
            "professional and precise"
            if formality > 6
            else ("friendly and relaxed" if formality < 4 else "balanced and conversational")
        )

        length = (
            "1-2 sentences"
            if brevity > 7
            else ("2-4 sentences" if detail_level < 5 else "3-5 sentences with details")
        )

        wit_level = "clever when appropriate" if brevity < 7 else "straightforward"

        # Mood-based response adjustment
        mood_guidance = {
            "frustrated": (
                "The user seems frustrated. Be EXTRA supportive and patient. "
                "Acknowledge their struggle: 'I can see this is tricky.' "
                "Focus on clear solutions. Offer to break down complex steps. "
                "Stay encouraging: 'Let's tackle this together.'"
            ),
            "stressed": (
                "The user seems stressed or under pressure. Be CALM and efficient. "
                "Get straight to the solution without extra fluff. "
                "Reassure them: 'I'll help you fix this quickly.' "
                "Prioritize actionable steps."
            ),
            "happy": (
                "The user seems happy or satisfied! Match their positive energy. "
                "Be enthusiastic and engaging. Use upbeat language. "
                "Celebrate their success: 'Nice! That's great progress!'"
            ),
            "excited": (
                "The user seems excited! Match their enthusiasm. "
                "Be energetic and encouraging. "
                "Build on their momentum: 'Yes! Let's make this awesome!'"
            ),
            "neutral": "",
        }

        mood_instruction = mood_guidance.get(mood, "")

        # Omni persona activation
        omni_active = getattr(settings, "enable_omni_persona", True)
        persona_name = "AuraIA OmniDev" if omni_active else "Assistant"

        # Emoji usage rules
        if emoji_cfg["allow"] and emoji_cfg["max"] > 0:
            emoji_rule = (
                "Emojis allowed as prosody (max "
                f"{emoji_cfg['max']}). Avoid in code, file paths, URLs. "
                "Use context-matched emojis: support (🙏), success (🎉), "
                "momentum (🚀), idea (💡), celebration (✨), calm (🌿)."
            )
        else:
            emoji_rule = "Do not use emojis in this response."

        traits = (
            "Traits: warm, clear, collaborative, patient, humble, proactive; "
            "pair-programmer mindset; empower user with small, safe steps."
        )

        base_instruction = (
            f"You are {persona_name}, a supportive engineering partner. "
            f"Be {tone}. Keep responses to {length}. "
            f"Be {wit_level} and highly responsive. MIRROR the user's style. "
            f"{traits} {emoji_rule}"
        )

        if mood_instruction:
            return f"{base_instruction}\n\nMOOD ADAPTATION: {mood_instruction}"
        return base_instruction

    def _build_system_prompt(
        self, task_type: TaskType, description: str = "", content: str = ""
    ) -> str:
        """Build system prompt with mode-specific focus and adaptive personality."""
        prompts = {
            # CODE FOCUS: Output code only, minimal explanation
            TaskType.CODE_GENERATION: (
                "You are a code generator. OUTPUT ONLY CODE with "
                "brief inline comments. "
                "No explanations, no markdown formatting around code blocks. "
                "Be direct and implementation-focused."
            ),
            # DEBUG FOCUS: Show bug + fix, no theory
            TaskType.BUG_FIX: (
                "You are a debugger. FORMAT: 1) Identify the bug in 1 sentence. "
                "2) Provide fixed code. 3) Add 1 sentence why the fix works. "
                "Stay technical and focused."
            ),
            # REFACTOR FOCUS: Before/After comparison
            TaskType.REFACTOR: (
                "You are a code optimizer. FORMAT: 1) State the issue (1 line). "
                "2) Show refactored code. 3) List improvements (max 3 bullet points). "
                "Focus on the technical changes."
            ),
            # TEST FOCUS: Generate tests, minimal prose
            TaskType.TEST_GENERATION: (
                "You are a test engineer. OUTPUT: Test code with descriptive "
                "test names. Include edge cases and assertions. "
                "Keep explanations minimal."
            ),
            # DOCUMENTATION FOCUS: Concise technical explanation
            TaskType.DOCUMENTATION: (
                "You are a code explainer. FORMAT: 1) What it does (1 sentence). "
                "2) Key logic (2-3 points). 3) Notable patterns or issues (1 line). "
                "Stay technical, avoid verbosity."
            ),
        }

        # For CHAT/GENERAL mode, use adaptive personality and optional external persona
        if task_type not in prompts:
            user_style = self._analyze_user_style(description, content)
            base_prompt = self._build_adaptive_chat_prompt(user_style)

            # Try to blend with external AuraIA_Persona engine if enabled
            try:
                omni_active = getattr(settings, "enable_omni_persona", True)
                assets_dir = getattr(settings, "persona_assets_dir", None)
                if omni_active and assets_dir:
                    # local import; persona assets may be disabled
                    from src.services import persona_adapter

                    prepared = persona_adapter.prepare_chat_prompts(
                        user_message=f"{description}\n\n{content}".strip(),
                        persona_name="AuraIA OmniDev",
                        sentiment=user_style.get("mood", "neutral"),
                        empathy=0.7 if user_style.get("needs_support") else 0.4,
                        archetype_weights=None,
                    )
                    persona_prompt = prepared.get("system_prompt", "").strip()
                    if persona_prompt:
                        # Merge: persona rules first, then adaptive style constraints
                        return f"{persona_prompt}\n\n{base_prompt}".strip()
            except Exception:  # noqa: BLE001
                # Fallback to internal adaptive prompt only
                pass

            return base_prompt

        return prompts[task_type]

    def _build_user_prompt(self, description: str, content: str, _task_type: TaskType) -> str:
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
            Suggested adjustment focuses on readability and maintainability
            while keeping the original intent intact.
            Confidence is derived from static analysis heuristics that inspect
            the supplied code and task type.
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
            except Exception as e:  # noqa: BLE001
                ws_logger.warning("LLM verification failed, using fallback: %s", e, exc_info=True)
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
        llm = self.llm_manager
        assert llm is not None
        verification_result = await llm.generate(
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

        return VerificationSummary(status=status, confidence=confidence, metadata=metadata)

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

        return VerificationSummary(status=status, confidence=confidence, metadata=metadata)


class TaskOrchestrator:
    """
    Coordinates task execution with multi-model routing and full pipeline.

    Orchestrates: Context → Reasoning → Verification → Safety → Composition → Metrics
    """

    def __init__(
        self,
        reasoner: Optional[SimpleReasonerEngine] = None,
        verifier: Optional[SimpleVerifierEngine] = None,
        llm_manager=None,
        router: Optional[MultiModelRouter] = None,
        safety_layer=None,
        output_composer=None,
        context_engine=None,
        metrics_service=None,
        rag_retrievers: Optional[Dict[str, Any]] = None,
        memory_service: Optional[MemoryService] = None,
    ):
        """
        Initialize orchestrator with full service pipeline.

        Args:
            reasoner: Custom reasoner engine (optional)
            verifier: Custom verifier engine (optional)
            llm_manager: LLM Manager for model execution
            router: Multi-Model Router for intelligent model selection
            safety_layer: Safety validation service
            output_composer: Output composition service
            context_engine: Context and embedding service
            metrics_service: Performance metrics service
            rag_retrievers: Optional LangChain retriever bundle for experimental RAG v2
        """
        self.router = router or MultiModelRouter()
        self.llm_manager = llm_manager
        self._reasoner = reasoner or SimpleReasonerEngine(
            llm_manager=llm_manager, router=self.router
        )
        self._verifier = verifier or SimpleVerifierEngine(
            llm_manager=llm_manager, router=self.router
        )
        self.safety_layer = safety_layer
        self.output_composer = output_composer
        self.context_engine = context_engine
        self.metrics_service = metrics_service
        self._rag_retrievers = rag_retrievers
        self._memory_service = memory_service
        self._rag_enabled = bool(settings.experimental_rag_v2_enabled and rag_retrievers)

        if settings.experimental_rag_v2_enabled:
            if self._rag_enabled:
                ws_logger.info(
                    "experimental_rag_v2_active",
                    extra={"rag_stage": "langchain_retriever"},
                )
            else:
                ws_logger.warning(
                    "experimental_rag_v2_unavailable",
                    extra={"reason": "missing_retrievers"},
                )
        self._token_cache: Dict[str, List[str]] = {}
        self._token_cache_max = 1000
        self._retrieval_cache: Optional[OrderedDict[str, List[str]]] = None
        self._retrieval_cache_cap = 100

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
                "duration_ms": round(duration_ms, 2),
                "verification_status": (
                    verification_summary.status.value
                    if verification_summary
                    else VerificationStatus.SKIPPED.value
                ),
            },
        )

        return result

    # --- Helper proxies for tests (adaptive style/emoji/persona) ---
    def _analyze_user_style(self, description: str, content: str) -> dict:  # pragma: no cover
        """Expose reasoner's style analyzer for unit tests."""
        return self._reasoner._analyze_user_style(  # type: ignore[attr-defined]
            description, content
        )

    def _emoji_policy(self, user_style: dict) -> dict:  # pragma: no cover
        """Expose reasoner's emoji policy for unit tests."""
        return self._reasoner._emoji_policy(user_style)  # type: ignore[attr-defined]

    def _build_adaptive_chat_prompt(self, user_style: dict) -> str:  # pragma: no cover
        """Expose reasoner's adaptive chat prompt builder for unit tests."""
        return self._reasoner._build_adaptive_chat_prompt(user_style)  # type: ignore[attr-defined]

    def _build_system_prompt(  # pragma: no cover
        self, task_type: TaskType, description: str = "", content: str = ""
    ) -> str:
        """Expose reasoner's system prompt generator for unit tests."""
        return self._reasoner._build_system_prompt(  # type: ignore[attr-defined]
            task_type, description, content
        )

    async def execute_task(self, request: TaskRequestPayload) -> TaskSessionResult:
        """
        Execute task with full pipeline: Context → Reason → Verify → Safety → Compose

        This is the enhanced version that uses all AuralA services.

        Args:
            request: Task request payload

        Returns:
            Complete task result with safety and composition
        """
        start_time = time.perf_counter()
        pipeline_metadata: Dict[str, Any] = {
            "stages": [],
            "models_used": [],
            "latencies": {},
        }
        latencies = cast(
            Dict[str, float],
            pipeline_metadata["latencies"],
        )  # type: ignore[index]
        stages = cast(
            List[str],
            pipeline_metadata["stages"],
        )  # type: ignore[index]
        models_used = cast(
            List[str],
            pipeline_metadata["models_used"],
        )  # type: ignore[index]

        ws_logger.info(
            "enhanced_task_execution_started",
            extra={
                "task_id": request.id,
                "task_type": request.type.value,
            },
        )

        # Stage 1: Context Retrieval (if context engine available)
        context_snippets: List[str] = []
        context_source: Optional[str] = None
        if self._retrieval_cache is None:
            self._retrieval_cache = OrderedDict()

        if self._rag_enabled and request.content:
            try:
                # Start with retrievers provided by DI (typically includes 'code')
                retrievers: Dict[str, Any] = dict(self._rag_retrievers or {})

                # If a memory service is available and we can infer a session_id,
                # augment with memory retriever
                session_id: Optional[str] = None
                try:
                    # Prefer explicit metadata session_id if provided
                    session_id = (request.metadata or {}).get("session_id") or (
                        (
                            getattr(request, "context", None)
                            and getattr(request.context, "metadata", {})
                            or {}
                        ).get("session_id")
                    )
                except Exception:  # noqa: BLE001
                    session_id = None

                # Resolve a memory service if possible (injected or singleton)
                mem_service = self._memory_service
                if mem_service is None and session_id:
                    try:
                        mem_service = await get_memory_service()
                    except Exception:  # pragma: no cover - optional dependency
                        mem_service = None

                if mem_service and session_id:
                    # Build only the memory retriever to avoid duplicating code
                    # retriever
                    mem_retr = build_retriever_dict(
                        memory_service=mem_service, session_id=session_id
                    ).get("memory")
                    if mem_retr is not None:
                        retrievers.setdefault("memory", mem_retr)

                if "code" not in retrievers:
                    raise RuntimeError("LangChain code retriever is not configured")

                t0 = time.perf_counter()

                # Simple retrieval cache key to avoid recomputation in rapid repeats
                key = "|".join(
                    [
                        request.content,
                        str(getattr(settings, "fusion_weight_vector", 0.6)),
                        str(getattr(settings, "fusion_weight_bm25", 0.4)),
                        str(getattr(settings, "hybrid_fusion_enabled", False)),
                        str(getattr(settings, "relevance_threshold", 0.0)),
                        str(bool(getattr(settings, "reranker_model", ""))),
                        str(getattr(settings, "rag_v2_code_top_k", 5)),
                    ]
                )

                cached = self._retrieval_cache.get(key)
                if cached is not None:
                    context_snippets = cached
                else:
                    # Fetch from available retrievers (code + optional memory)
                    code_docs = await retrievers["code"].aget_relevant_documents(request.content)

                    mem_docs: List[Any] = []
                    if retrievers.get("memory") is not None:
                        try:
                            mem_retr = retrievers["memory"]
                            mem_docs = await mem_retr.aget_relevant_documents(request.content)
                        except Exception as mem_err:  # noqa: BLE001
                            ws_logger.warning("Memory retriever failed: %s", mem_err)

                    # Optional hybrid fusion + reranking for code documents
                    def _tokenize(text: str) -> List[str]:
                        return [t for t in text.lower().split() if t]

                    def _lexical_overlap(query: str, doc: str) -> float:
                        q = _tokenize(query)
                        d = _tokenize(doc)
                        if not q or not d:
                            return 0.0
                        inter = len(set(q) & set(d))
                        # normalized overlap proxy
                        return inter / max(len(set(q)), 1)

                    def _vector_score(doc: Any) -> float:
                        try:
                            meta = getattr(doc, "metadata", {}) or {}
                            score = float(meta.get("relevance", 0.0) or 0.0)
                            return max(0.0, min(1.0, score))
                        except Exception:
                            return 0.0

                    ranked_code: List[Tuple[float, Any]] = []
                    w_bm25 = getattr(settings, "fusion_weight_bm25", 0.4)
                    w_vec = getattr(settings, "fusion_weight_vector", 0.6)
                    use_hybrid = bool(getattr(settings, "hybrid_fusion_enabled", False))
                    # Optional BM25 scoring if library is available
                    bm25_scores: Optional[List[float]] = None
                    max_bm25: float = 1.0
                    code_texts: List[str] = [getattr(d, "page_content", "") for d in code_docs]
                    if use_hybrid:
                        try:  # pragma: no cover - optional dependency
                            from rank_bm25 import BM25Okapi  # type: ignore

                            corpus = [_tokenize(txt) for txt in code_texts]
                            bm25 = BM25Okapi(corpus)
                            q_tokens = _tokenize(request.content)
                            bm25_arr = bm25.get_scores(q_tokens)
                            bm25_scores = [float(s) for s in bm25_arr]
                            max_bm25 = max(max(bm25_scores) if bm25_scores else 1.0, 1.0)
                        except Exception:  # noqa: BLE001
                            bm25_scores = None

                    for idx, d in enumerate(code_docs):
                        v = _vector_score(d)
                        doc_text = code_texts[idx]
                        if use_hybrid:
                            if bm25_scores is not None:
                                lex = bm25_scores[idx] / max_bm25 if max_bm25 > 0 else 0.0
                            else:
                                lex = _lexical_overlap(request.content, doc_text)
                        else:
                            lex = 0.0
                        score = (w_vec * v) + (w_bm25 * lex) if use_hybrid else v
                        ranked_code.append((score, d))
                        # Trace each candidate prior to filtering (mark as considered)
                        try:
                            retrieval_trace_buffer.append(
                                RetrievalDocTrace(
                                    file=(getattr(d, "metadata", {}) or {}).get("file")
                                    or (getattr(d, "metadata", {}) or {}).get("source"),
                                    vector_score=v,
                                    lexical_score=lex,
                                    fusion_score=score,
                                    kept_after_threshold=False,
                                    extras={
                                        "id": ((getattr(d, "metadata", {}) or {}).get("id")),
                                        "stage": "rag_v2",
                                        "event": "considered",
                                    },
                                )
                            )
                        except Exception:  # noqa: BLE001
                            pass

                    # Reranker toggle: honor relevance_threshold when enabled
                    reranker_on = bool(getattr(settings, "reranker_model", ""))
                    threshold = float(getattr(settings, "relevance_threshold", 0.0) or 0.0)
                    if reranker_on:
                        # Optional cross-encoder reranker blending
                        ce_scores: Optional[List[float]] = None
                        try:  # pragma: no cover - optional dependency
                            model_name = str(getattr(settings, "reranker_model", ""))
                            if model_name.lower().startswith("cross-encoder"):
                                from sentence_transformers import (
                                    CrossEncoder,
                                )  # type: ignore  # noqa: E501

                                loop = asyncio.get_event_loop()
                                ce = await loop.run_in_executor(
                                    None, lambda: CrossEncoder(model_name)
                                )
                                pairs = [(request.content, t) for t in code_texts]
                                # Predict in executor to avoid blocking
                                raw_scores = await loop.run_in_executor(
                                    None, lambda: ce.predict(pairs)
                                )
                                # Normalize to 0..1
                                try:
                                    raw_list = [float(x) for x in raw_scores]
                                    mn, mx = min(raw_list), max(raw_list)
                                    span = (mx - mn) or 1.0
                                    ce_scores = [(x - mn) / span for x in raw_list]
                                except Exception:  # noqa: BLE001
                                    ce_scores = None
                        except Exception:  # noqa: BLE001
                            ce_scores = None

                        if ce_scores is not None:
                            # Blend CE score into fusion score then threshold
                            blended: List[Tuple[float, Any]] = []
                            for i, (s, d) in enumerate(ranked_code):
                                ce_s = ce_scores[i] if i < len(ce_scores) else 0.0
                                new_s = 0.5 * s + 0.5 * ce_s
                                blended.append((new_s, d))
                            ranked_code = [(s, d) for (s, d) in blended if s >= threshold]
                        else:
                            ranked_code = [(s, d) for (s, d) in ranked_code if s >= threshold]

                    # Sort by score desc and clip to top_k
                    ranked_code.sort(key=lambda x: x[0], reverse=True)
                    top_k = int(getattr(settings, "rag_v2_code_top_k", 5) or 5)
                    ranked_code = ranked_code[:top_k]

                    # Observability: compute kept/filtered counts and mean fusion
                    considered_count = len(code_docs)
                    kept_count = len(ranked_code)
                    filtered_count = max(considered_count - kept_count, 0)
                    mean_fusion = (
                        sum(s for (s, _d) in ranked_code) / kept_count if kept_count else 0.0
                    )

                    # Build final snippets: code (reranked) + memory (as-is)
                    context_snippets = [
                        getattr(d, "page_content", "")
                        for (s, d) in ranked_code
                        if getattr(d, "page_content", "")
                    ]
                    # Trace kept documents after thresholding/top-k
                    try:
                        for s, d in ranked_code:
                            retrieval_trace_buffer.append(
                                RetrievalDocTrace(
                                    file=(getattr(d, "metadata", {}) or {}).get("file")
                                    or (getattr(d, "metadata", {}) or {}).get("source"),
                                    vector_score=_vector_score(d),
                                    lexical_score=(
                                        _lexical_overlap(
                                            request.content,
                                            getattr(d, "page_content", ""),
                                        )
                                        if use_hybrid and bm25_scores is None
                                        else 0.0
                                    ),
                                    fusion_score=s,
                                    kept_after_threshold=True,
                                    extras={
                                        "id": ((getattr(d, "metadata", {}) or {}).get("id")),
                                        "stage": "rag_v2",
                                        "event": "kept",
                                    },
                                )
                            )
                    except Exception:  # noqa: BLE001
                        pass
                    context_snippets.extend(
                        [
                            getattr(doc, "page_content", "")
                            for doc in mem_docs
                            if getattr(doc, "page_content", "")
                        ]
                    )
                    # Populate cache
                    self._retrieval_cache[key] = context_snippets
                    # Enforce simple LRU capacity
                    cap = getattr(self, "_retrieval_cache_cap", 100)
                    while len(self._retrieval_cache) > cap:
                        self._retrieval_cache.popitem(last=False)

                    # Attach retrieval stats
                    try:
                        pipeline_metadata["retrieval_stats"] = {
                            "considered": considered_count,
                            "kept": kept_count,
                            "filtered": filtered_count,
                            "topk_mean_fusion": round(mean_fusion, 4),
                        }
                    except Exception:  # noqa: BLE001
                        pass
                    # Export to Prometheus if available
                    try:  # pragma: no cover - optional
                        from src.main import (
                            RETRIEVAL_DOCS_CONSIDERED,
                            RETRIEVAL_DOCS_KEPT,
                            RETRIEVAL_TOPK_MEAN_FUSION_SCORE,
                        )

                        RETRIEVAL_DOCS_CONSIDERED.labels(stage="rag_v2").inc(considered_count)
                        RETRIEVAL_DOCS_KEPT.labels(stage="rag_v2").inc(kept_count)
                        RETRIEVAL_TOPK_MEAN_FUSION_SCORE.labels(stage="rag_v2").set(
                            float(mean_fusion)
                        )
                    except Exception:  # noqa: BLE001
                        pass

                latencies["context_retrieval"] = time.perf_counter() - t0
                stages.append("rag_v2_retrieval")
                context_source = "rag_v2"
                pipeline_metadata["retriever"] = context_source
                ws_logger.debug(
                    "Retrieved %d context snippets via LangChain retrievers",
                    len(context_snippets),
                )
            except Exception as e:  # noqa: BLE001
                ws_logger.warning("LangChain context retrieval failed: %s", e)

        if not context_snippets and self.context_engine and request.content:
            try:
                t0 = time.perf_counter()
                context_snippets = await self.context_engine.get_context_snippets(
                    request.content, top_k=3
                )
                latencies["context_retrieval"] = time.perf_counter() - t0
                stages.append("context_retrieval")
                context_source = "context_engine"
                pipeline_metadata["retriever"] = context_source
                ws_logger.debug("Retrieved %d context snippets", len(context_snippets))
            except Exception as e:  # noqa: BLE001
                ws_logger.warning("Context retrieval failed: %s", e)

        if context_snippets and context_source:
            request.metadata.setdefault("retrieval", {})
            request.metadata["retrieval"].update(
                {
                    "source": context_source,
                    "snippet_count": len(context_snippets),
                }
            )

        # Stage 2: Reasoning (System 1 Fast)
        t0 = time.perf_counter()
        agent_response = await self._reasoner.generate(request)
        latencies["reasoning"] = time.perf_counter() - t0
        stages.append("reasoning")

        # Extract model used from metadata
        if hasattr(agent_response, "metadata") and agent_response.metadata:
            model = agent_response.metadata.get("selected_model", "unknown")
            models_used.append(model)

        # Stage 3: Verification (System 2 Deep)
        verification_summary = None
        if self._verifier:
            t0 = time.perf_counter()
            verification_summary = await self._verifier.verify(request, agent_response)
            latencies["verification"] = time.perf_counter() - t0
            stages.append("verification")

        # Stage 4: Safety Check
        safety_result = None
        if self.safety_layer and agent_response.suggestions:
            try:
                t0 = time.perf_counter()
                code_text = agent_response.suggestions[0].code
                safety_result = await self.safety_layer.check_safety(code_text)
                latencies["safety"] = time.perf_counter() - t0
                stages.append("safety")
                pipeline_metadata["safety_passed"] = safety_result.get("safe", True)

                if not safety_result.get("safe"):
                    ws_logger.warning(
                        "Safety check failed for task %s: %s",
                        request.id,
                        safety_result.get("reason", "Unknown"),
                    )
            except Exception as e:  # noqa: BLE001
                ws_logger.error("Safety check failed: %s", e)
                safety_result = {"safe": True, "raw": f"Error: {e}"}

        # Stage 5: Output Composition (Tone Enhancement)
        final_output = None
        if self.output_composer and agent_response.suggestions:
            try:
                t0 = time.perf_counter()
                system1_text = agent_response.suggestions[0].code
                system2_text = (
                    verification_summary.metadata.get("verifier_output", "")
                    if verification_summary
                    else None
                )

                composition = await self.output_composer.compose(
                    system1_text=system1_text,
                    system2_text=system2_text,
                    use_premium_tone=True,
                    safety_result=safety_result,
                )
                final_output = composition.get("final_text", system1_text)
                latencies["composition"] = time.perf_counter() - t0
                stages.append("composition")
                models_used.extend(composition.get("used_models", []))

                # Update the suggestion with composed output
                if final_output and agent_response.suggestions:
                    agent_response.suggestions[0].code = final_output

            except Exception as e:  # noqa: BLE001
                ws_logger.error("Output composition failed: %s", e)

        # Stage 6: Metrics Recording
        total_duration = time.perf_counter() - start_time
        if self.metrics_service:
            try:
                for model in models_used:
                    model_latency = latencies.get("reasoning", 0.0)
                    self.metrics_service.record_call(
                        model=model,
                        latency=model_latency,
                        success=bool(agent_response.suggestions),
                    )
            except Exception as e:  # noqa: BLE001
                ws_logger.error("Metrics recording failed: %s", e)

        # Build final result
        duration_ms = total_duration * 1000
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
                "pipeline": pipeline_metadata,
            },
        )

        ws_logger.info(
            "enhanced_task_execution_completed",
            extra={
                "task_id": request.id,
                "duration_ms": round(duration_ms, 2),
                "stages": pipeline_metadata["stages"],
                "models_used": pipeline_metadata["models_used"],
                "safety_passed": pipeline_metadata.get("safety_passed", True),
            },
        )

        return result

    def _build_summary(
        self,
        agent_response: AgentResponse,
        verification_summary: Optional[VerificationSummary],
    ) -> str:
        primary_suggestion = agent_response.suggestions[0] if agent_response.suggestions else None
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
            "No actionable suggestions were produced by the orchestrator. " f"{verification_text}"
        )


__all__ = ["TaskOrchestrator", "SimpleReasonerEngine", "SimpleVerifierEngine"]
