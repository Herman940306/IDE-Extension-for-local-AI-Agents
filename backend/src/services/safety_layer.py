"""
Safety Layer - Content Moderation and Security Checks
Project Creator: Herman Swanepoel

Uses phi3:mini for safety validation of generated outputs.
Checks for: harmful actions, privacy leaks, insecure code, disallowed content.
"""

from __future__ import annotations

import logging
import time
from typing import Any, Dict

logger = logging.getLogger(__name__)


class SafetyLayer:
    """
    Content moderation layer using phi3:mini for safety checks.

    Validates outputs for:
    - Harmful or dangerous actions
    - Privacy/data leaks
    - Insecure code patterns
    - Disallowed content
    """

    def __init__(self, llm_manager=None):
        """
        Initialize safety layer with LLM manager.

        Args:
            llm_manager: LLM Manager for model execution
        """
        self.llm_manager = llm_manager
        self.safety_model = "phi3:mini"
        logger.info("Safety Layer initialized with model: %s", self.safety_model)

    async def check_safety(self, candidate_text: str) -> Dict[str, Any]:
        """
        Run safety check on candidate output text.

        Args:
            candidate_text: Text to validate for safety

        Returns:
            Dict with keys:
                - safe (bool): Whether content passed safety checks
                - raw (str): Raw safety model response
                - latency (float): Check duration in seconds
                - reason (str): Explanation if unsafe
        """
        if not self.llm_manager:
            logger.warning("Safety check skipped: no LLM manager available")
            return {
                "safe": True,
                "raw": "Safety check bypassed (no LLM manager)",
                "latency": 0.0,
                "reason": "",
            }

        prompt = self._build_safety_prompt(candidate_text)

        start_time = time.time()
        try:
            response_text = await self.llm_manager.generate(
                prompt=prompt,
                system_prompt=(
                    "You are a safety validator. Respond with SAFE or UNSAFE " "followed by reason."
                ),
                model=self.safety_model,
                temperature=0.1,  # Very low for consistent safety checks
                max_tokens=500,
            )
            latency = time.time() - start_time

            # Parse response
            response_upper = response_text.upper()
            is_safe = "UNSAFE" not in response_upper and "DANGEROUS" not in response_upper

            # Extract reason if unsafe
            reason = ""
            if not is_safe:
                reason = response_text.strip()

            logger.info(
                "Safety check completed: %s (%.2fs)",
                "SAFE" if is_safe else "UNSAFE",
                latency,
            )

            return {
                "safe": is_safe,
                "raw": response_text,
                "latency": latency,
                "reason": reason,
            }

        except Exception as e:
            latency = time.time() - start_time
            logger.error("Safety check failed: %s", e, exc_info=True)
            # Fail-safe: reject on error
            return {
                "safe": False,
                "raw": f"Safety check error: {str(e)}",
                "latency": latency,
                "reason": "Safety check encountered an error",
            }

    def _build_safety_prompt(self, candidate_text: str) -> str:
        """Build safety validation prompt."""
        return f"""SAFETY REVIEW:
Check the following output for potential issues:
(a) Harmful or dangerous actions
(b) Privacy leaks or data exposure
(c) Insecure code patterns
(d) Disallowed or inappropriate content

Reply with SAFE or UNSAFE followed by a brief reason.

OUTPUT TO REVIEW:
{candidate_text}

ASSESSMENT:"""

    async def check_code_security(self, code: str, language: str = "python") -> Dict[str, Any]:
        """
        Specialized security check for code snippets.

        Args:
            code: Code snippet to validate
            language: Programming language

        Returns:
            Dict with safety assessment and security issues found
        """
        if not self.llm_manager:
            return {
                "safe": True,
                "issues": [],
                "latency": 0.0,
            }

        prompt = f"""SECURITY CODE REVIEW ({language}):
Analyze this code for security vulnerabilities:
- SQL injection risks
- Command injection risks
- Unsafe file operations
- Hardcoded credentials
- Unsafe deserialization
- Missing input validation

CODE:
{code}

List any security issues found, or reply SECURE if none found."""

        start_time = time.time()
        try:
            response_text = await self.llm_manager.generate(
                prompt=prompt,
                system_prompt=("You are a security code reviewer. Be thorough but concise."),
                model=self.safety_model,
                temperature=0.1,
                max_tokens=800,
            )
            latency = time.time() - start_time

            response_upper = response_text.upper()
            is_secure = "SECURE" in response_upper or "NO ISSUES" in response_upper

            # Extract issues if found
            issues = []
            if not is_secure:
                # Parse issues from response
                lines = response_text.strip().split("\n")
                issues = [
                    line.strip()
                    for line in lines
                    if line.strip() and not line.strip().startswith("#")
                ]

            return {
                "safe": is_secure,
                "issues": issues,
                "raw": response_text,
                "latency": latency,
            }

        except Exception as e:
            latency = time.time() - start_time
            logger.error("Code security check failed: %s", e, exc_info=True)
            return {
                "safe": False,
                "issues": [f"Security check error: {str(e)}"],
                "raw": "",
                "latency": latency,
            }
