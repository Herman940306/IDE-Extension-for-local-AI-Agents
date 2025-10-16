"""
LLM Manager with Ollama support and Response Caching
Project Creator: Herman Swanepoel
"""

import asyncio
import logging
from enum import Enum
from typing import TYPE_CHECKING, Any, Dict, List, Optional, cast

try:  # Optional dependency: present when local Ollama support is installed
    import ollama  # type: ignore
except ImportError:  # pragma: no cover - exercised via missing dependency path
    ollama = None  # type: ignore

if TYPE_CHECKING:  # pragma: no cover - typing aid only
    from types import ModuleType

from src.services.response_cache import ResponseCache

logger = logging.getLogger(__name__)


class LLMError(Exception):
    """Base exception for LLM-related errors"""


class LLMProvider(str, Enum):
    """Supported LLM providers"""

    OLLAMA = "ollama"
    OPENAI = "openai"
    ANTHROPIC = "anthropic"


class LLMManager:
    """
    Manages LLM interactions with support for local (Ollama) and cloud providers
    """

    def __init__(
        self,
        provider: LLMProvider = LLMProvider.OLLAMA,
        model: str = "codellama:7b",
        base_url: str = "http://localhost:11434",
        api_key: Optional[str] = None,
        allow_cloud: bool = False,
        response_cache: Optional[ResponseCache] = None,
        enable_cache: bool = True,
    ):
        """
        Initialize LLM Manager

        Args:
            provider: LLM provider to use
            model: Model name
            base_url: Base URL for Ollama
            api_key: API key for cloud providers
            allow_cloud: Whether to allow cloud fallback
            response_cache: ResponseCache instance for caching
            enable_cache: Whether to enable response caching
        """
        self.provider = provider
        self.model = model
        self.base_url = base_url
        self.api_key = api_key
        self.allow_cloud = allow_cloud
        self.ollama_client = None
        self.response_cache = response_cache
        self.enable_cache = enable_cache and response_cache is not None

        logger.info(
            f"LLM Manager initialized with provider: {provider}, model: {model}, "
            f"cache_enabled: {self.enable_cache}"
        )

    def _ensure_ollama_available(self) -> "ModuleType | Any":
        """Ensure the optional Ollama dependency is installed."""
        if ollama is None:
            raise LLMError(
                "Ollama integration requires optional dependencies. "
                "Install them via `pip install -r backend/requirements-ollama.txt`."
            )
        return cast("ModuleType | Any", ollama)

    async def initialize(self) -> None:
        """Initialize the LLM provider"""
        if self.provider == LLMProvider.OLLAMA:
            try:
                self._ensure_ollama_available()
                # Test connection to Ollama
                await self._test_ollama_connection()
                logger.info("✓ Ollama connection successful")
            except Exception as e:
                logger.error(f"Failed to connect to Ollama: {e}")
                if self.allow_cloud:
                    logger.warning(
                        "Ollama unavailable, cloud fallback enabled but not implemented yet"
                    )
                else:
                    raise Exception("Ollama unavailable and cloud fallback disabled")

    async def _test_ollama_connection(self) -> None:
        """Test connection to Ollama server"""
        client = self._ensure_ollama_available()
        try:
            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            await loop.run_in_executor(None, client.list)
        except Exception as e:
            raise Exception(f"Cannot connect to Ollama at {self.base_url}: {e}")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
        use_cloud: bool = False,
        use_cache: bool = True,
    ) -> str:
        """
        Generate text using the LLM with optional caching

        Args:
            prompt: User prompt
            system_prompt: System prompt for context
            temperature: Sampling temperature (0.0 to 1.0)
            max_tokens: Maximum tokens to generate
            stop: Stop sequences
            use_cloud: Force cloud usage (if allowed)
            use_cache: Whether to use cache for this request

        Returns:
            Generated text
        """
        # Check cache first if enabled
        if self.enable_cache and use_cache and self.response_cache is not None:
            context_params = {
                "system_prompt": system_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stop": stop,
                "provider": self.provider.value,
            }

            cached_response = await self.response_cache.get(
                prompt=prompt, model=self.model, context_params=context_params
            )

            if cached_response:
                logger.info(
                    "Cache hit for LLM request",
                    extra={
                        "model": self.model,
                        "prompt_length": len(prompt),
                        "cache_enabled": True,
                    },
                )
                return cached_response["response"]["text"]

        # Generate response
        if use_cloud and not self.allow_cloud:
            logger.warning("Cloud usage requested but not allowed, using local")
            use_cloud = False

        if self.provider == LLMProvider.OLLAMA and not use_cloud:
            response_text = await self._generate_ollama(
                prompt, system_prompt, temperature, max_tokens, stop
            )
        elif use_cloud:
            response_text = await self._generate_cloud(
                prompt, system_prompt, temperature, max_tokens, stop
            )
        else:
            raise ValueError(f"Unsupported provider: {self.provider}")

        # Cache the response if enabled
        if self.enable_cache and use_cache and response_text and self.response_cache is not None:
            context_params = {
                "system_prompt": system_prompt,
                "temperature": temperature,
                "max_tokens": max_tokens,
                "stop": stop,
                "provider": self.provider.value,
            }

            await self.response_cache.set(
                prompt=prompt,
                model=self.model,
                response={"text": response_text},
                context_params=context_params,
            )

            logger.info(
                "Cached LLM response",
                extra={
                    "model": self.model,
                    "prompt_length": len(prompt),
                    "response_length": len(response_text),
                },
            )

        return response_text

    async def _generate_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        stop: Optional[List[str]],
    ) -> str:
        """Generate using Ollama"""
        client = self._ensure_ollama_available()
        try:
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            options: Dict[str, Any] = {
                "temperature": temperature,
            }

            if max_tokens:
                options["num_predict"] = max_tokens

            if stop:
                options["stop"] = stop

            # Run in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.chat(
                    model=self.model,
                    messages=messages,
                    options=options,
                ),
            )

            return response["message"]["content"]

        except Exception as e:
            logger.error(f"Ollama generation failed: {e}")
            if self.allow_cloud:
                logger.info("Falling back to cloud provider")
                return await self._generate_cloud(
                    prompt, system_prompt, temperature, max_tokens, stop
                )
            else:
                raise LLMError(f"LLM generation failed: {e}") from e

    async def _generate_cloud(
        self,
        prompt: str,
        system_prompt: Optional[str],
        temperature: float,
        max_tokens: Optional[int],
        stop: Optional[List[str]],
    ) -> str:
        """Generate using cloud provider (placeholder)"""
        # TODO: Implement cloud providers (OpenAI, Anthropic)
        raise NotImplementedError("Cloud providers not yet implemented")

    async def generate_streaming(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
    ):
        """
        Generate text with streaming response

        Args:
            prompt: User prompt
            system_prompt: System prompt
            temperature: Sampling temperature
            max_tokens: Maximum tokens
            stop: Stop sequences

        Yields:
            Text chunks as they are generated
        """
        if self.provider == LLMProvider.OLLAMA:
            client = self._ensure_ollama_available()
            messages = []

            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})

            messages.append({"role": "user", "content": prompt})

            options: Dict[str, Any] = {
                "temperature": temperature,
            }

            if max_tokens:
                options["num_predict"] = max_tokens

            if stop:
                options["stop"] = stop

            try:
                # Stream response
                stream = client.chat(
                    model=self.model, messages=messages, options=options, stream=True
                )

                for chunk in stream:
                    if "message" in chunk and "content" in chunk["message"]:
                        yield chunk["message"]["content"]

            except Exception as e:
                logger.error(f"Streaming generation failed: {e}")
                raise Exception(f"LLM streaming failed: {e}")
        else:
            raise NotImplementedError("Streaming only supported for Ollama currently")

    def get_available_models(self) -> List[str]:
        """
        Get list of available models

        Returns:
            List of model names
        """
        if self.provider == LLMProvider.OLLAMA:
            client = self._ensure_ollama_available()
            try:
                models = client.list()
                return [model["name"] for model in models.get("models", [])]
            except Exception as e:
                logger.error(f"Failed to list models: {e}")
                return []
        else:
            return []

    def get_model_info(self) -> Dict[str, Any]:
        """
        Get information about current model

        Returns:
            Model information dictionary
        """
        return {
            "provider": self.provider.value,
            "model": self.model,
            "base_url": self.base_url if self.provider == LLMProvider.OLLAMA else None,
            "allow_cloud": self.allow_cloud,
            "cache_enabled": self.enable_cache,
        }

    async def get_cache_stats(self) -> Dict[str, Any]:
        """
        Get cache statistics

        Returns:
            Cache statistics dictionary
        """
        if self.response_cache:
            return await self.response_cache.get_stats()
        return {"enabled": False, "message": "Cache not configured"}

    async def clear_cache(self) -> bool:
        """
        Clear all cached responses

        Returns:
            True if cleared successfully, False otherwise
        """
        if self.response_cache:
            return await self.response_cache.clear()
        return False

    async def health_check(self) -> bool:
        """
        Check if LLM service is healthy

        Returns:
            True if healthy, False otherwise
        """
        try:
            if self.provider == LLMProvider.OLLAMA:
                await self._test_ollama_connection()
                return True
            return False
        except Exception as e:
            logger.error(f"Health check failed: {e}")
            return False
