"""
Output Composer - Final Response Composition Layer
Project Creator: Herman Swanepoel

Merges System 1 (fast) + System 2 (verify) responses with UX tone enhancement.
Applies AuralA personality: calm, elegant, human-centric communication.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict, Optional

logger = logging.getLogger(__name__)


class OutputComposer:
    """
    Final composition layer that merges multi-model outputs with tone enhancement.

    Execution flow:
    1. Merge System 1 (fast reasoning) + System 2 (verification) outputs
    2. Apply UX tone enhancement using Gemma3 for warmth and clarity
    3. Ensure technical accuracy is preserved
    4. Return refined, human-friendly response
    """

    def __init__(self, llm_manager=None):
        """
        Initialize output composer with LLM manager.

        Args:
            llm_manager: LLM Manager for model execution
        """
        self.llm_manager = llm_manager
        self.tone_model_premium = "gemma3:12b"
        self.tone_model_light = "gemma3:4b"
        logger.info("Output Composer initialized with tone models")

    async def compose(
        self,
        system1_text: str,
        system2_text: Optional[str] = None,
        code_text: Optional[str] = None,
        use_premium_tone: bool = True,
        safety_result: Optional[Dict] = None,
    ) -> Dict[str, Any]:
        """
        Compose final output from multi-model responses.

        Args:
            system1_text: Fast reasoning output (System 1)
            system2_text: Verification/deep reasoning output (System 2)
            code_text: Code generation output (if applicable)
            use_premium_tone: Use premium (12B) vs light (4B) tone model
            safety_result: Safety check results to include

        Returns:
            Dict with keys:
                - final_text (str): Composed and tone-enhanced output
                - tone_raw (str): Raw tone model output
                - used_models (list): Models used in composition
                - latency (float): Composition duration
        """
        start_time = time.time()

        # Select best available content
        base_content = self._select_best_content(system1_text, system2_text, code_text)

        if not base_content.strip():
            logger.warning("Output composer received empty content")
            return {
                "final_text": "",
                "tone_raw": "",
                "used_models": [],
                "latency": time.time() - start_time,
            }

        # Apply tone enhancement if LLM manager available
        if self.llm_manager:
            tone_result = await self._apply_tone_enhancement(
                base_content, use_premium_tone
            )
            latency = time.time() - start_time

            return {
                "final_text": tone_result.get("enhanced_text", base_content),
                "tone_raw": tone_result.get("raw_response", ""),
                "used_models": tone_result.get("models_used", []),
                "latency": latency,
            }
        else:
            # Fallback: return base content without tone enhancement
            logger.debug("Tone enhancement skipped: no LLM manager")
            return {
                "final_text": base_content,
                "tone_raw": "",
                "used_models": [],
                "latency": time.time() - start_time,
            }

    def _select_best_content(
        self,
        system1_text: str,
        system2_text: Optional[str],
        code_text: Optional[str],
    ) -> str:
        """
        Select the best available content for composition.
        Priority: system2 (verified) > code > system1 (fast)
        """
        # Prefer verified content from System 2
        if system2_text and system2_text.strip():
            return system2_text.strip()

        # Then code generation output
        if code_text and code_text.strip():
            return code_text.strip()

        # Fallback to System 1 fast reasoning
        return system1_text.strip() if system1_text else ""

    async def _apply_tone_enhancement(
        self, content: str, use_premium: bool
    ) -> Dict[str, Any]:
        """Apply AuralA personality tone enhancement."""
        tone_model = self.tone_model_premium if use_premium else self.tone_model_light

        prompt = self._build_tone_prompt(content)
        system_prompt = self._build_tone_system_prompt()

        try:
            response_text = await self.llm_manager.generate(
                prompt=prompt,
                system_prompt=system_prompt,
                model=tone_model,
                temperature=0.8,  # Higher temp for warmth and natural variation
                max_tokens=2000,
            )

            enhanced = response_text.strip() if response_text else content

            logger.info("Tone enhancement completed using %s", tone_model)

            return {
                "enhanced_text": enhanced,
                "raw_response": response_text,
                "models_used": [tone_model],
            }

        except Exception as e:
            logger.error(
                "Tone enhancement failed: %s (falling back to base content)", e
            )
            return {
                "enhanced_text": content,
                "raw_response": "",
                "models_used": [],
            }

    def _build_tone_prompt(self, content: str) -> str:
        """Build tone enhancement prompt."""
        return f"""You are AuralA's tone enhancement layer.

Your task: Refine the following output to be calm, elegant, and human-centric.

IMPORTANT RULES:
- Do NOT modify code blocks (triple backticks ``` or single backticks `)
- Preserve all technical details and accuracy
- Keep explanations clear and concise
- Add warmth and professionalism to natural language
- Remove any robotic or overly formal phrasing
- Maintain the original structure and meaning

INPUT:
{content}

Return only the refined output (no meta-commentary):"""

    def _build_tone_system_prompt(self) -> str:
        """Build system prompt for tone enhancement."""
        return """You are AuralA, a calm and insightful AI coding partner.

Your communication style:
- Warm but professional
- Clear and concise
- Empathetic and supportive
- Technically accurate
- No unnecessary jargon
- Natural, conversational tone

You help developers create better code with confidence and clarity."""

    async def compose_error_response(
        self, error_message: str, context: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Compose a user-friendly error response.

        Args:
            error_message: Technical error message
            context: Optional context about what was being attempted

        Returns:
            Composed error response with helpful guidance
        """
        prompt = f"""Convert this technical error into a helpful, user-friendly message:

ERROR: {error_message}
CONTEXT: {context or 'General operation'}

Provide:
1. What went wrong (simple terms)
2. Possible cause
3. Suggested next step

Keep it brief and supportive."""

        try:
            response = await self.llm_manager.generate(
                prompt=prompt,
                system_prompt=self._build_tone_system_prompt(),
                model=self.tone_model_light,  # Use light model for errors
                temperature=0.7,
                max_tokens=300,
            )

            return {
                "final_text": response,
                "tone_raw": response,
                "used_models": [self.tone_model_light],
                "latency": 0.0,
            }

        except Exception as e:
            logger.error("Error response composition failed: %s", e)
            # Fallback to simple error message
            fallback = (
                f"I encountered an issue: {error_message}\n\n"
                f"Please check the logs for more details."
            )
            return {
                "final_text": fallback,
                "tone_raw": "",
                "used_models": [],
                "latency": 0.0,
            }
