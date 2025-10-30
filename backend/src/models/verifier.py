"""
System 2: Analytical Verifier using Mistral 7B
Project Creator: Herman Swanepoel
"""

import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class VerificationRequest(BaseModel):
    """Request for analytical verification"""

    code: str
    language: str
    context: str
    original_task: str
    system1_confidence: float


class VerificationResponse(BaseModel):
    """Response from analytical verifier"""

    valid: bool
    confidence: float
    issues: List[Dict[str, Any]]
    suggestions: List[str]
    reasoning: str
    latency_ms: float
    model: str


class AnalyticalVerifier:
    """
    System 2: Slow, analytical verification for complex tasks.

    Uses Mistral 7B (Q4_K_M) for thorough analysis with target
    latency <2000ms for complex refactors and validations.
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "mistral:7b",
        timeout: float = 60.0,
    ):
        """
        Initialize analytical verifier.

        Args:
            ollama_url: Ollama API URL
            model: Model name
            timeout: Request timeout in seconds
        """
        self.ollama_url = ollama_url
        self.model = model
        self.timeout = timeout
        # Use granular timeouts: allow long read/write during model warm-up
        try:
            http_timeout = httpx.Timeout(
                connect=10.0,
                read=timeout,
                write=timeout,
                pool=10.0,
            )
        except Exception:
            http_timeout = timeout  # Fallback to simple float
        self.client = httpx.AsyncClient(timeout=http_timeout)

        # Performance tracking
        self.total_verifications = 0
        self.total_latency = 0.0
        self.rejections = 0

        logger.info(f"AnalyticalVerifier initialized with {model}")

    async def verify(self, request: VerificationRequest) -> VerificationResponse:
        """
        Perform analytical verification.

        Args:
            request: Verification request

        Returns:
            Verification response
        """
        start_time = time.time()

        try:
            # Build verification prompt
            prompt = self._build_verification_prompt(request)

            # Call Ollama
            response = await self._call_ollama(prompt)

            # Parse verification result
            is_valid, issues, suggestions = self._parse_verification(response)

            # Calculate confidence
            confidence = self._calculate_confidence(is_valid, issues, request.system1_confidence)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Update stats
            self.total_verifications += 1
            self.total_latency += latency_ms
            if not is_valid:
                self.rejections += 1

            logger.info(
                f"Verification complete: {latency_ms:.0f}ms, "
                f"valid={is_valid}, conf={confidence:.2f}"
            )

            return VerificationResponse(
                valid=is_valid,
                confidence=confidence,
                issues=issues,
                suggestions=suggestions,
                reasoning=response.get("reasoning", "Analytical verification"),
                latency_ms=latency_ms,
                model=self.model,
            )

        except Exception as e:
            logger.error(f"Verification failed: {e}")
            latency_ms = (time.time() - start_time) * 1000

            return VerificationResponse(
                valid=False,
                confidence=0.0,
                issues=[{"type": "error", "message": str(e)}],
                suggestions=[],
                reasoning=f"Verification failed: {str(e)}",
                latency_ms=latency_ms,
                model=self.model,
            )

    def _build_verification_prompt(self, request: VerificationRequest) -> str:
        """Build verification prompt"""
        prompt = f"""You are an expert code reviewer.
Analyze the following code for correctness, quality, and potential issues.

Original Task: {request.original_task}

Language: {request.language}

Context:
{request.context}

Code to Verify:
```{request.language}
{request.code}
```

Analyze the code for:
1. Correctness: Does it solve the task correctly?
2. Logic: Are there any logical errors?
3. Edge cases: Are edge cases handled?
4. Best practices: Does it follow best practices?
5. Security: Are there any security concerns?

Provide your analysis in this format:
VALID: [YES/NO]
ISSUES: [List any issues found]
SUGGESTIONS: [List improvements]
REASONING: [Explain your analysis]

Analysis:"""

        return prompt

    async def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Call Ollama API with retries and device-aware options"""
        settings = get_settings()
        max_retries = max(0, int(settings.ollama_max_retries))
        backoff = max(0.0, float(settings.ollama_retry_backoff_seconds))

        attempt = 0
        last_exc: Optional[Exception] = None
        while attempt <= max_retries:
            try:
                # Default keep-alive for System 2; override for advanced model
                keep_alive = getattr(settings, "verifier_keep_alive", "10m")
                options: Dict[str, Any] = {
                    "temperature": 0.3,  # Lower temperature for verification
                    "top_p": 0.9,
                    "num_predict": 1000,
                }

                # If using the advanced model, prefer CPU and unload immediately
                if self.model == getattr(settings, "advanced_model", ""):
                    if getattr(settings, "advanced_force_cpu", True):
                        options["num_gpu"] = 0  # Force CPU execution
                    keep_alive = getattr(settings, "advanced_keep_alive", "0")

                payload: Dict[str, Any] = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": keep_alive,
                    "options": options,
                }

                response = await self.client.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()

                result = response.json()
                return {
                    "text": result.get("response", ""),
                    "reasoning": "Analytical verification",
                }

            except httpx.TimeoutException as e:
                last_exc = e
                if attempt == max_retries:
                    logger.warning("Ollama verification timed out (final)")
                    break
                delay = backoff * (2**attempt)
                logger.warning(
                    f"Ollama verification timed out (attempt "
                    f"{attempt+1}/{max_retries+1}), retrying in {delay:.1f}s"
                )
                time.sleep(delay)
                attempt += 1
            except httpx.HTTPStatusError as e:
                last_exc = e
                status = e.response.status_code if e.response is not None else None
                if status and 500 <= status < 600 and attempt < max_retries:
                    delay = backoff * (2**attempt)
                    logger.warning(
                        f"Ollama verification 5xx ({status}) on attempt "
                        f"{attempt+1}/{max_retries+1}, retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue
                logger.error(f"Ollama verification HTTP error: {e}")
                raise
            except Exception as e:
                logger.error(f"Ollama verification failed: {e}")
                raise

        assert last_exc is not None
        raise last_exc

    def _parse_verification(
        self, response: Dict[str, Any]
    ) -> tuple[bool, List[Dict[str, Any]], List[str]]:
        """Parse verification response"""
        text = response.get("text", "")

        # Extract validity
        is_valid = "VALID: YES" in text.upper() or "VALID:YES" in text.upper()

        # Extract issues
        issues = []
        if "ISSUES:" in text.upper():
            issues_section = text.split("ISSUES:")[1].split("SUGGESTIONS:")[0]
            issue_lines = [line.strip() for line in issues_section.split("\n") if line.strip()]
            for line in issue_lines[:5]:  # Limit to 5 issues
                if line and not line.startswith("REASONING"):
                    issues.append(
                        {
                            "type": "warning",
                            "message": line.lstrip("- ").lstrip("* "),
                        }
                    )

        # Extract suggestions
        suggestions = []
        if "SUGGESTIONS:" in text.upper():
            suggestions_section = text.split("SUGGESTIONS:")[1].split("REASONING:")[0]
            suggestion_lines = [
                line.strip() for line in suggestions_section.split("\n") if line.strip()
            ]
            suggestions = [
                line.lstrip("- ").lstrip("* ")
                for line in suggestion_lines[:3]  # Limit to 3 suggestions
                if line and not line.startswith("REASONING")
            ]

        return is_valid, issues, suggestions

    def _calculate_confidence(
        self, is_valid: bool, issues: List[Dict[str, Any]], system1_confidence: float
    ) -> float:
        """Calculate verification confidence"""
        # Start with high confidence for System 2
        confidence = 0.9

        # Penalize for issues found
        confidence -= len(issues) * 0.05

        # If invalid, lower confidence
        if not is_valid:
            confidence = min(confidence, 0.7)

        # Consider System 1 confidence
        # If System 1 was confident and we agree, boost confidence
        if is_valid and system1_confidence > 0.8:
            confidence = min(confidence + 0.05, 1.0)

        return max(confidence, 0.0)

    def get_stats(self) -> Dict[str, Any]:
        """Get verification statistics"""
        avg_latency = (
            self.total_latency / self.total_verifications if self.total_verifications > 0 else 0
        )

        rejection_rate = (
            self.rejections / self.total_verifications if self.total_verifications > 0 else 0
        )

        return {
            "model": self.model,
            "total_verifications": self.total_verifications,
            "avg_latency_ms": avg_latency,
            "rejections": self.rejections,
            "rejection_rate": rejection_rate,
        }

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
