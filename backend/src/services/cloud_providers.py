"""
Cloud LLM provider implementations
Project Creator: Herman Swanepoel
"""

from __future__ import annotations

import asyncio
import importlib
import logging
from abc import ABC, abstractmethod
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class CloudProviderError(Exception):
    """Base exception for cloud provider errors."""


class ProviderConfigurationError(CloudProviderError):
    """Raised when provider configuration is invalid."""


class ProviderDependencyError(CloudProviderError):
    """Raised when an optional dependency is missing."""


class CloudProvider(ABC):
    """Base class for cloud LLM providers."""

    def __init__(self, api_key: str, model: str):
        self.api_key = api_key
        self.model = model

    @abstractmethod
    def _client_ready(self) -> bool:
        """Return True when the provider client is initialised."""

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
    ) -> str:
        """Generate text using the cloud provider."""

    @abstractmethod
    async def health_check(self) -> bool:
        """Check if the provider is available."""


class OpenAIProvider(CloudProvider):
    """OpenAI API provider with optional dependency handling."""

    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        self._client_mode: Optional[str] = None
        self._client: Optional[object] = None

    def _ensure_client(self) -> object:
        if self._client is not None:
            return self._client

        if not self.api_key:
            raise ProviderConfigurationError(
                "OpenAI provider requires an API key. Set one before generating text."
            )

        try:
            module = importlib.import_module("openai")
        except ImportError as exc:  # pragma: no cover - optional dependency branch
            raise ProviderDependencyError(
                "OpenAI provider requires the optional 'openai' package. Install it via "  # noqa: E501
                "`pip install openai`."
            ) from exc

        async_client_cls = getattr(module, "AsyncOpenAI", None)
        sync_client_cls = getattr(module, "OpenAI", None)
        chat_completion = getattr(module, "ChatCompletion", None)

        if async_client_cls is not None:
            self._client_mode = "async"
            self._client = async_client_cls(api_key=self.api_key)
        elif sync_client_cls is not None:
            self._client_mode = "sync"
            self._client = sync_client_cls(api_key=self.api_key)
        elif chat_completion is not None:
            self._client_mode = "legacy"
            self._client = module
            module.api_key = self.api_key
        else:  # pragma: no cover - defensive branch
            raise ProviderDependencyError(
                "The installed 'openai' package does not expose a supported client interface."  # noqa: E501
            )

        return self._client

    def _client_ready(self) -> bool:
        return self._client is not None

    @staticmethod
    def _extract_content(response: object) -> str:
        choices = getattr(response, "choices", None)
        if choices is None and isinstance(response, dict):
            choices = response.get("choices")  # type: ignore[assignment]

        if not choices:
            raise CloudProviderError("OpenAI response did not include any choices.")

        first_choice = choices[0]
        message = getattr(first_choice, "message", None)
        if message is None and isinstance(first_choice, dict):
            message = first_choice.get("message")

        if message is None:
            text_val = getattr(first_choice, "text", None)
            if text_val is None and isinstance(first_choice, dict):
                text_val = first_choice.get("text")
            if isinstance(text_val, str) and text_val.strip():
                return text_val.strip()
            raise CloudProviderError("OpenAI response missing message content.")

        content = getattr(message, "content", None)
        if content is None and isinstance(message, dict):
            content = message.get("content")

        if isinstance(content, list):
            parts = []
            for item in content:
                text_val = getattr(item, "text", None)
                if text_val is None and isinstance(item, dict):
                    text_val = item.get("text")
                if isinstance(text_val, str):
                    parts.append(text_val)
            content = "".join(parts)

        if isinstance(content, str) and content.strip():
            return content.strip()

        raise CloudProviderError("OpenAI response content was empty.")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
    ) -> str:
        client = self._ensure_client()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        request_kwargs: Dict[str, object] = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
        }

        if max_tokens is not None:
            request_kwargs["max_tokens"] = max_tokens
        if stop:
            request_kwargs["stop"] = stop

        try:
            if self._client_mode == "async":
                response = await client.chat.completions.create(**request_kwargs)
            elif self._client_mode == "sync":
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(  # type: ignore[arg-type]
                    None, lambda: client.chat.completions.create(**request_kwargs)
                )
            else:
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None,
                    lambda: client.ChatCompletion.create(**request_kwargs),
                )
        except ProviderDependencyError:
            raise
        except Exception as exc:  # pragma: no cover - depends on remote API
            raise CloudProviderError(f"OpenAI request failed: {exc}") from exc

        return self._extract_content(response)

    async def health_check(self) -> bool:
        try:
            self._ensure_client()
            return True
        except CloudProviderError as exc:
            logger.warning("OpenAI health check failed: %s", exc)
            return False


class AnthropicProvider(CloudProvider):
    """Anthropic (Claude) API provider with optional dependency handling."""

    DEFAULT_MAX_TOKENS = 1024

    def __init__(self, api_key: str, model: str):
        super().__init__(api_key, model)
        self._client_mode: Optional[str] = None
        self._client: Optional[object] = None

    def _ensure_client(self) -> object:
        if self._client is not None:
            return self._client

        if not self.api_key:
            raise ProviderConfigurationError(
                "Anthropic provider requires an API key. Set one before generating text."  # noqa: E501
            )

        try:
            module = importlib.import_module("anthropic")
        except ImportError as exc:  # pragma: no cover - optional dependency branch
            raise ProviderDependencyError(
                "Anthropic provider requires the optional 'anthropic' package. Install it via "  # noqa: E501
                "`pip install anthropic`."
            ) from exc

        async_client_cls = getattr(module, "AsyncAnthropic", None)
        sync_client_cls = getattr(module, "Anthropic", None)

        if async_client_cls is not None:
            self._client_mode = "async"
            self._client = async_client_cls(api_key=self.api_key)
        elif sync_client_cls is not None:
            self._client_mode = "sync"
            self._client = sync_client_cls(api_key=self.api_key)
        else:  # pragma: no cover - defensive branch
            raise ProviderDependencyError(
                "The installed 'anthropic' package does not expose a supported client interface."  # noqa: E501
            )

        return self._client

    def _client_ready(self) -> bool:
        return self._client is not None

    @staticmethod
    def _extract_content(response: object) -> str:
        content = getattr(response, "content", None)
        if isinstance(content, list):
            parts = []
            for item in content:
                text_val = getattr(item, "text", None)
                if text_val is None and isinstance(item, dict):
                    text_val = item.get("text")
                if isinstance(text_val, str):
                    parts.append(text_val)
            if parts:
                return "".join(parts).strip()

        completion = getattr(response, "completion", None)
        if isinstance(completion, str) and completion.strip():
            return completion.strip()

        if isinstance(response, dict):
            completion = response.get("completion")
            if isinstance(completion, str) and completion.strip():
                return completion.strip()

            content_blocks = response.get("content")
            if isinstance(content_blocks, list):
                parts = []
                for item in content_blocks:
                    text_val = getattr(item, "text", None)
                    if text_val is None and isinstance(item, dict):
                        text_val = item.get("text")
                    if isinstance(text_val, str):
                        parts.append(text_val)
                if parts:
                    return "".join(parts).strip()

        raise CloudProviderError("Anthropic response content was empty.")

    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stop: Optional[List[str]] = None,
    ) -> str:
        client = self._ensure_client()

        request_kwargs: Dict[str, object] = {
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": temperature,
            "max_tokens": max_tokens or self.DEFAULT_MAX_TOKENS,
        }

        if system_prompt:
            request_kwargs["system"] = system_prompt
        if stop:
            request_kwargs["stop_sequences"] = stop

        try:
            if self._client_mode == "async":
                response = await client.messages.create(**request_kwargs)
            else:
                loop = asyncio.get_running_loop()
                response = await loop.run_in_executor(
                    None, lambda: client.messages.create(**request_kwargs)
                )
        except ProviderDependencyError:
            raise
        except Exception as exc:  # pragma: no cover - depends on remote API
            raise CloudProviderError(f"Anthropic request failed: {exc}") from exc

        return self._extract_content(response)

    async def health_check(self) -> bool:
        try:
            self._ensure_client()
            return True
        except CloudProviderError as exc:
            logger.warning("Anthropic health check failed: %s", exc)
            return False


class PrivacyManager:
    """Manages privacy controls for cloud LLM usage."""

    def __init__(self, allow_cloud: bool = False):
        self.allow_cloud = allow_cloud
        self.sensitive_patterns = [
            r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}",  # Email
            r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b",  # Phone
            r"\b\d{3}-\d{2}-\d{4}\b",  # SSN
            r"(?i)(password|secret|key|token)\s*[:=]\s*[^\s]+",  # Secrets
            r"sk-[a-zA-Z0-9]{48}",  # API keys
        ]

    def can_use_cloud(self, code: str) -> tuple[bool, Optional[str]]:
        if not self.allow_cloud:
            return False, "Cloud usage disabled"

        import re

        for pattern in self.sensitive_patterns:
            if re.search(pattern, code):
                return False, "Code contains sensitive data"

        return True, None

    def sanitize_code(self, code: str) -> str:
        import re

        sanitized = code
        patterns_replacements = [
            (r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}", "[EMAIL_REDACTED]"),
            (r"\b\d{3}[-.]?\d{3}[-.]?\d{4}\b", "[PHONE_REDACTED]"),
            (r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
            (r"(?i)(password|secret|key|token)\s*[:=]\s*[^\s]+", r"\1=[REDACTED]"),
            (r"sk-[a-zA-Z0-9]{48}", "[API_KEY_REDACTED]"),
        ]

        for pattern, replacement in patterns_replacements:
            sanitized = re.sub(pattern, replacement, sanitized)

        return sanitized
