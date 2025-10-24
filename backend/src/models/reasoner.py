"""
System 1: Fast Reasoner using LLaMA 3.2 3B
Project Creator: Herman Swanepoel
"""

import logging
import time
from typing import Any, Dict, List, Optional

import httpx
from pydantic import BaseModel

from ..config.settings import get_settings

logger = logging.getLogger(__name__)


class ReasoningRequest(BaseModel):
    """Request for fast reasoning"""

    task_type: str
    description: str
    code_context: str
    language: str
    selected_text: Optional[str] = None
    max_tokens: int = 500


class ReasoningResponse(BaseModel):
    """Response from fast reasoner"""

    suggestions: List[str]
    confidence: float
    reasoning: str
    latency_ms: float
    model: str


class FastReasoner:
    """
    System 1: Fast, intuitive reasoning for simple tasks.

    Uses LLaMA 3.2 3B (Q4_K_M) for rapid inference with target
    latency <200ms for simple completions and refactors.
    """

    def __init__(
        self,
        ollama_url: str = "http://localhost:11434",
        model: str = "llama3.2:3b",
        timeout: float = 30.0,
    ):
        """
        Initialize fast reasoner.

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
        self.total_requests = 0
        self.total_latency = 0.0
        self.cache_hits = 0

        logger.info(f"FastReasoner initialized with {model}")

    async def reason(self, request: ReasoningRequest) -> ReasoningResponse:
        """
        Perform fast reasoning on the request.

        Args:
            request: Reasoning request

        Returns:
            Reasoning response with suggestions
        """
        start_time = time.time()

        try:
            # Build prompt
            prompt = self._build_prompt(request)

            # Call Ollama
            response = await self._call_ollama(prompt)

            # Parse response
            suggestions = self._parse_suggestions(response)
            confidence = self._calculate_confidence(response, request)

            # Calculate latency
            latency_ms = (time.time() - start_time) * 1000

            # Update stats
            self.total_requests += 1
            self.total_latency += latency_ms

            logger.info(
                f"Fast reasoning complete: {latency_ms:.0f}ms, "
                f"conf={confidence:.2f}"
            )

            return ReasoningResponse(
                suggestions=suggestions,
                confidence=confidence,
                reasoning=response.get("reasoning", "Fast heuristic reasoning"),
                latency_ms=latency_ms,
                model=self.model,
            )

        except Exception as e:
            logger.error(f"Fast reasoning failed: {e}")
            latency_ms = (time.time() - start_time) * 1000

            return ReasoningResponse(
                suggestions=[],
                confidence=0.0,
                reasoning=f"Reasoning failed: {str(e)}",
                latency_ms=latency_ms,
                model=self.model,
            )

    def _build_prompt(self, request: ReasoningRequest) -> str:
        """Build prompt for the model"""
        prompt = f"""Task: {request.task_type}
Description: {request.description}

Language: {request.language}

Code Context:
```{request.language}
{request.code_context}
```
"""

        if request.selected_text:
            prompt += f"""
Focus on this specific code:
```{request.language}
{request.selected_text}
```
"""

        prompt += (
            "\n"
            "Provide a concise, actionable suggestion. "
            "Be specific and include code examples if applicable.\n\n"
            "Suggestion:"
        )

        return prompt

    async def _call_ollama(self, prompt: str) -> Dict[str, Any]:
        """Call Ollama API with keep-alive and device-aware options"""
        settings = get_settings()
        max_retries = max(0, int(settings.ollama_max_retries))
        backoff = max(0.0, float(settings.ollama_retry_backoff_seconds))

        attempt = 0
        last_exc: Optional[Exception] = None
        while attempt <= max_retries:
            try:
                # Reasoner is GPU-resident; apply keep_alive to keep it warm
                payload: Dict[str, Any] = {
                    "model": self.model,
                    "prompt": prompt,
                    "stream": False,
                    "keep_alive": getattr(settings, "reasoner_keep_alive", "30m"),
                    "options": {
                        "temperature": 0.7,
                        "top_p": 0.9,
                        "num_predict": 500,
                    },
                }

                response = await self.client.post(
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                )
                response.raise_for_status()

                result = response.json()
                return {
                    "text": result.get("response", ""),
                    "reasoning": "Fast heuristic reasoning",
                }

            except httpx.TimeoutException as e:
                last_exc = e
                if attempt == max_retries:
                    logger.warning("Ollama request timed out (final)")
                    break
                delay = backoff * (2**attempt)
                logger.warning(
                    f"Ollama request timed out (attempt {attempt+1}/{max_retries+1}), "
                    f"retrying in {delay:.1f}s"
                )
                time.sleep(delay)
                attempt += 1
            except httpx.HTTPStatusError as e:
                # Retry on 5xx only
                last_exc = e
                status = e.response.status_code if e.response is not None else None
                if status and 500 <= status < 600 and attempt < max_retries:
                    delay = backoff * (2**attempt)
                    logger.warning(
                        f"Ollama 5xx ({status}) on attempt "
                        f"{attempt+1}/{max_retries+1}, retrying in {delay:.1f}s"
                    )
                    time.sleep(delay)
                    attempt += 1
                    continue
                logger.error(f"Ollama API HTTP error: {e}")
                raise
            except Exception as e:
                logger.error(f"Ollama API call failed: {e}")
                raise

        assert last_exc is not None
        raise last_exc

    def _parse_suggestions(self, response: Dict[str, Any]) -> List[str]:
        """Parse suggestions from model response"""
        text = response.get("text", "")

        # Extract code blocks
        import re

        code_blocks = re.findall(r"```[\w]*\n(.*?)```", text, re.DOTALL)

        if code_blocks:
            return [block.strip() for block in code_blocks]

        # If no code blocks, return the text as a suggestion
        if text.strip():
            return [text.strip()]

        return []

    def _calculate_confidence(
        self, response: Dict[str, Any], request: ReasoningRequest
    ) -> float:
        """Calculate confidence score"""
        # Base confidence for System 1
        confidence = 0.75

        # Increase for simple tasks
        simple_tasks = ["explain", "comment", "format"]
        if request.task_type.lower() in simple_tasks:
            confidence += 0.1

        # Decrease for complex tasks
        complex_tasks = ["refactor", "optimize", "debug"]
        if request.task_type.lower() in complex_tasks:
            confidence -= 0.1

        # Check if response has code
        if "```" in response.get("text", ""):
            confidence += 0.05

        return min(max(confidence, 0.0), 1.0)

    def get_stats(self) -> Dict[str, Any]:
        """Get performance statistics"""
        avg_latency = (
            self.total_latency / self.total_requests if self.total_requests > 0 else 0
        )

        return {
            "model": self.model,
            "total_requests": self.total_requests,
            "avg_latency_ms": avg_latency,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": (
                self.cache_hits / self.total_requests if self.total_requests > 0 else 0
            ),
        }

    async def close(self):
        """Close HTTP client"""
        await self.client.aclose()
        await self.client.aclose()
