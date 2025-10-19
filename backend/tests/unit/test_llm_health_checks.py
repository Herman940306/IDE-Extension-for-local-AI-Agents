"""
Health check coverage for LLM services
Project Creator: Herman Swanepoel
"""

from unittest.mock import AsyncMock

import pytest
from src.services.cloud_providers import (
    AnthropicProvider,
    CloudProviderError,
    OpenAIProvider,
    ProviderConfigurationError,
)
from src.services.llm_manager import LLMManager, LLMProvider


@pytest.mark.asyncio
async def test_openai_health_check_success(monkeypatch):
    provider = OpenAIProvider(api_key="test-key", model="gpt-4o")
    monkeypatch.setattr(provider, "_ensure_client", lambda: object())

    assert await provider.health_check() is True


@pytest.mark.asyncio
async def test_openai_health_check_handles_configuration_error(monkeypatch):
    provider = OpenAIProvider(api_key="", model="gpt-4o")

    def raise_configuration_error():
        raise ProviderConfigurationError("missing key")

    monkeypatch.setattr(provider, "_ensure_client", raise_configuration_error)

    assert await provider.health_check() is False


@pytest.mark.asyncio
async def test_anthropic_health_check_handles_dependency_error(monkeypatch):
    provider = AnthropicProvider(api_key="test-key", model="claude-3-opus")

    def raise_configuration_error():
        raise ProviderConfigurationError("anthropic missing")

    monkeypatch.setattr(provider, "_ensure_client", raise_configuration_error)

    assert await provider.health_check() is False


@pytest.mark.asyncio
async def test_llm_manager_health_check_ollama_failure(monkeypatch):
    manager = LLMManager(provider=LLMProvider.OLLAMA)
    manager._test_ollama_connection = AsyncMock(  # type: ignore[attr-defined]
        side_effect=Exception("ollama down")
    )

    assert await manager.health_check() is False


@pytest.mark.asyncio
async def test_llm_manager_health_check_cloud_failure(monkeypatch):
    manager = LLMManager(provider=LLMProvider.OPENAI, api_key="test", allow_cloud=True)
    fake_provider = AsyncMock()
    fake_provider.health_check = AsyncMock(side_effect=CloudProviderError("unavailable"))

    monkeypatch.setattr(manager, "_get_cloud_provider", lambda _: fake_provider)

    assert await manager.health_check() is False
    fake_provider.health_check.assert_awaited()


@pytest.mark.asyncio
async def test_llm_manager_health_check_disallows_cloud_when_disabled():
    manager = LLMManager(provider=LLMProvider.OPENAI, api_key="test", allow_cloud=False)

    assert await manager.health_check() is False
