"""
Unit tests for Critical Services (LLM Manager & Connection Manager)

Project Creator: Herman Swanepoel
Date: 2025-10-13
Target Coverage: 90%+
GODMODE: AUTONOMOUS EXECUTION - PHASE 3 BATCH 1
"""

import asyncio
from unittest.mock import AsyncMock, patch

import pytest
from fastapi import WebSocket
from src.services.connection_manager import ConnectionManager
from src.services.llm_manager import LLMError, LLMManager, LLMProvider

# ============================================================================
# LLM Manager Tests
# ============================================================================


class TestLLMManagerInitialization:
    """Test LLM Manager initialization"""

    def test_initialization_with_defaults(self):
        """Test initialization with default parameters"""
        manager = LLMManager()

        assert manager.provider == LLMProvider.OLLAMA
        assert manager.model == "codellama:7b"
        assert manager.base_url == "http://localhost:11434"
        assert manager.allow_cloud is False
        assert manager.enable_cache is False  # No cache provided

    def test_initialization_with_cache(self, mock_response_cache):
        """Test initialization with response cache"""
        manager = LLMManager(response_cache=mock_response_cache, enable_cache=True)

        assert manager.response_cache == mock_response_cache
        assert manager.enable_cache is True

    def test_initialization_with_custom_config(self):
        """Test initialization with custom configuration"""
        manager = LLMManager(
            provider=LLMProvider.OLLAMA,
            model="llama2:13b",
            base_url="http://custom:11434",
            allow_cloud=True,
        )

        assert manager.model == "llama2:13b"
        assert manager.base_url == "http://custom:11434"
        assert manager.allow_cloud is True


@pytest.mark.asyncio
class TestLLMManagerGeneration:
    """Test LLM generation functionality"""

    @patch("src.services.llm_manager.ollama")
    async def test_generate_success(self, mock_ollama):
        """Test successful text generation"""
        mock_ollama.chat.return_value = {"message": {"content": "Generated response"}}

        manager = LLMManager()
        result = await manager.generate("Test prompt")

        assert result == "Generated response"
        mock_ollama.chat.assert_called_once()

    @patch("src.services.llm_manager.ollama")
    async def test_generate_with_system_prompt(self, mock_ollama):
        """Test generation with system prompt"""
        mock_ollama.chat.return_value = {"message": {"content": "Response"}}

        manager = LLMManager()
        await manager.generate(
            "User prompt", system_prompt="You are a helpful assistant"
        )

        call_args = mock_ollama.chat.call_args
        messages = call_args.kwargs["messages"]

        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    @patch("src.services.llm_manager.ollama")
    async def test_generate_with_cache_hit(self, mock_ollama, mock_response_cache):
        """Test generation with cache hit"""
        mock_response_cache.get.return_value = {"response": {"text": "Cached response"}}

        manager = LLMManager(response_cache=mock_response_cache, enable_cache=True)

        result = await manager.generate("Test prompt")

        assert result == "Cached response"
        mock_ollama.chat.assert_not_called()  # Should not call LLM

    @patch("src.services.llm_manager.ollama")
    async def test_generate_with_cache_miss(self, mock_ollama, mock_response_cache):
        """Test generation with cache miss"""
        mock_response_cache.get.return_value = None
        mock_ollama.chat.return_value = {"message": {"content": "New response"}}

        manager = LLMManager(response_cache=mock_response_cache, enable_cache=True)

        result = await manager.generate("Test prompt")

        assert result == "New response"
        mock_ollama.chat.assert_called_once()
        mock_response_cache.set.assert_called_once()

    # B017: Use a specific exception for pytest.raises
    @patch("src.services.llm_manager.ollama")
    async def test_generate_with_b017(self, mock_ollama):
        """Test that exceptions are properly chained with 'from e'"""
        from src.services.llm_manager import LLMError

        class CustomTestException(Exception):
            pass

        mock_ollama.chat.side_effect = CustomTestException("Test error")
        manager = LLMManager()
        with pytest.raises(LLMError) as exc_info:  # noqa: B017
            await manager.generate("Test prompt")
        
        # Verify the original exception is chained
        assert exc_info.value.__cause__.__class__ == CustomTestException
        assert "Test error" in str(exc_info.value)

    @patch("src.services.llm_manager.ollama")
    async def test_generate_with_temperature(self, mock_ollama):
        """Test generation with custom temperature"""
        mock_ollama.chat.return_value = {"message": {"content": "Response"}}

        manager = LLMManager()
        await manager.generate("Test", temperature=0.9)

        call_args = mock_ollama.chat.call_args
        assert call_args.kwargs["options"]["temperature"] == 0.9

    @patch("src.services.llm_manager.ollama")
    async def test_generate_with_max_tokens(self, mock_ollama):
        """Test generation with max tokens"""
        mock_ollama.chat.return_value = {"message": {"content": "Response"}}

        manager = LLMManager()
        await manager.generate("Test", max_tokens=100)

        call_args = mock_ollama.chat.call_args
        assert call_args.kwargs["options"]["num_predict"] == 100

    @patch("src.services.llm_manager.ollama")
    async def test_generate_with_error(self, mock_ollama):
        """Test generation error handling"""
        mock_ollama.chat.side_effect = Exception("Ollama error")

        manager = LLMManager(allow_cloud=False)

        with pytest.raises(LLMError):
            await manager.generate("Test prompt")

    @patch("src.services.llm_manager.ollama")
    async def test_generate_cache_disabled(self, mock_ollama, mock_response_cache):
        """Test generation with cache disabled"""
        mock_ollama.chat.return_value = {"message": {"content": "Response"}}

        manager = LLMManager(response_cache=mock_response_cache, enable_cache=True)

        await manager.generate("Test", use_cache=False)

        mock_response_cache.get.assert_not_called()

    @pytest.mark.asyncio
    async def test_generate_with_openai_provider(self):
        """Test generation when using OpenAI provider"""
        fake_provider = AsyncMock()
        fake_provider.generate.return_value = "Cloud response"

        manager = LLMManager(
            provider=LLMProvider.OPENAI, api_key="test-key", allow_cloud=True
        )

        with patch.object(
            LLMManager, "_get_cloud_provider", return_value=fake_provider
        ) as mock_get_provider:
            result = await manager.generate("Test prompt")

        assert result == "Cloud response"
        mock_get_provider.assert_called_once()
        assert mock_get_provider.call_args.args[0] == LLMProvider.OPENAI
        fake_provider.generate.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_generate_cloud_requires_allow_flag(self):
        """Cloud provider should require allow_cloud flag"""
        manager = LLMManager(
            provider=LLMProvider.OPENAI, api_key="test-key", allow_cloud=False
        )

        with pytest.raises(LLMError):
            await manager.generate("Test prompt")

    @pytest.mark.asyncio
    async def test_generate_cloud_privacy_block(self):
        """Cloud usage should be blocked when sensitive data is detected"""
        manager = LLMManager(
            provider=LLMProvider.OPENAI, api_key="test-key", allow_cloud=True
        )

        with pytest.raises(LLMError):
            await manager.generate("Contact me at foo@example.com")

    @pytest.mark.asyncio
    async def test_generate_falls_back_to_cloud(self):
        """Fallback to cloud provider when Ollama fails"""
        fake_provider = AsyncMock()
        fake_provider.generate.return_value = "Cloud response"

        manager = LLMManager(api_key="test-key", allow_cloud=True)

        with (
            patch.object(
                LLMManager, "_generate_ollama", side_effect=LLMError("Ollama offline")
            ) as mock_ollama_generate,
            patch.object(
                LLMManager, "_get_cloud_provider", return_value=fake_provider
            ) as mock_get_provider,
        ):
            result = await manager.generate("Test prompt")

        assert result == "Cloud response"
        mock_ollama_generate.assert_awaited_once()
        mock_get_provider.assert_called_once()
        assert mock_get_provider.call_args.args[0] == LLMProvider.OPENAI
        fake_provider.generate.assert_awaited_once()


@pytest.mark.asyncio
class TestLLMManagerHealthCheck:
    """Test LLM health check functionality"""

    @patch("src.services.llm_manager.ollama")
    async def test_health_check_success(self, mock_ollama):
        """Test successful health check"""
        mock_ollama.list.return_value = {"models": []}

        manager = LLMManager()
        result = await manager.health_check()

        assert result is True

    @patch("src.services.llm_manager.ollama")
    async def test_health_check_failure(self, mock_ollama):
        """Test failed health check"""
        mock_ollama.list.side_effect = Exception("Connection error")

        manager = LLMManager()
        result = await manager.health_check()

        assert result is False


class TestLLMManagerModelInfo:
    """Test model information methods"""

    def test_get_model_info(self):
        """Test getting model information"""
        manager = LLMManager(model="llama2:7b", allow_cloud=True)

        info = manager.get_model_info()

        assert info["provider"] == "ollama"
        assert info["model"] == "llama2:7b"
        assert info["allow_cloud"] is True

    @patch("src.services.llm_manager.ollama")
    def test_get_available_models(self, mock_ollama):
        """Test getting available models"""
        mock_ollama.list.return_value = {
            "models": [{"name": "codellama:7b"}, {"name": "llama2:13b"}]
        }

        manager = LLMManager()
        models = manager.get_available_models()

        assert len(models) == 2
        assert "codellama:7b" in models
        assert "llama2:13b" in models

    @patch("src.services.llm_manager.ollama")
    def test_get_available_models_error(self, mock_ollama):
        """Test getting models with error"""
        mock_ollama.list.side_effect = Exception("Error")

        manager = LLMManager()
        models = manager.get_available_models()

        assert models == []


@pytest.mark.asyncio
class TestLLMManagerCacheOperations:
    """Test cache-related operations"""

    async def test_get_cache_stats_with_cache(self, mock_response_cache):
        """Test getting cache stats when cache is enabled"""
        mock_response_cache.get_stats.return_value = {"hits": 10, "misses": 5}

        manager = LLMManager(response_cache=mock_response_cache, enable_cache=True)

        stats = await manager.get_cache_stats()

        assert stats["hits"] == 10
        assert stats["misses"] == 5

    async def test_get_cache_stats_without_cache(self):
        """Test getting cache stats when cache is disabled"""
        manager = LLMManager()

        stats = await manager.get_cache_stats()

        assert stats["enabled"] is False

    async def test_clear_cache_with_cache(self, mock_response_cache):
        """Test clearing cache when cache is enabled"""
        mock_response_cache.clear.return_value = True

        manager = LLMManager(response_cache=mock_response_cache, enable_cache=True)

        result = await manager.clear_cache()

        assert result is True
        mock_response_cache.clear.assert_called_once()

    async def test_clear_cache_without_cache(self):
        """Test clearing cache when cache is disabled"""
        manager = LLMManager()

        result = await manager.clear_cache()

        assert result is False


class TestCloudProviderImplementations:
    """Tests for the optional cloud provider implementations"""

    @pytest.mark.asyncio
    async def test_openai_provider_missing_dependency(self, monkeypatch):
        """OpenAI provider should raise a clear error when dependency missing"""
        from src.services import cloud_providers as cp

        provider = cp.OpenAIProvider(api_key="test-key", model="gpt-4o")
        original_import = cp.importlib.import_module

        def fake_import(name, package=None):
            if name == "openai":
                raise ImportError("missing")
            return original_import(name, package)

        monkeypatch.setattr(cp.importlib, "import_module", fake_import)

        with pytest.raises(cp.ProviderDependencyError):
            await provider.generate("prompt")

    @pytest.mark.asyncio
    async def test_anthropic_provider_missing_dependency(self, monkeypatch):
        """Anthropic provider should raise when dependency missing"""
        from src.services import cloud_providers as cp

        provider = cp.AnthropicProvider(api_key="test-key", model="claude-3-opus")
        original_import = cp.importlib.import_module

        def fake_import(name, package=None):
            if name == "anthropic":
                raise ImportError("missing")
            return original_import(name, package)

        monkeypatch.setattr(cp.importlib, "import_module", fake_import)

        with pytest.raises(cp.ProviderDependencyError):
            await provider.generate("prompt")


# ============================================================================
# Connection Manager Tests
# ============================================================================


@pytest.fixture
def mock_websocket():
    """Create mock WebSocket"""
    ws = AsyncMock(spec=WebSocket)
    ws.accept = AsyncMock()
    ws.send_json = AsyncMock()
    return ws


class TestConnectionManagerInitialization:
    """Test Connection Manager initialization"""

    def test_initialization(self):
        """Test connection manager initialization"""
        manager = ConnectionManager()

        assert manager.active_connections == {}
        assert manager.connection_metadata == {}
        assert manager.get_connection_count() == 0


@pytest.mark.asyncio
class TestConnectionManagerConnect:
    """Test connection management"""

    async def test_connect_client(self, mock_websocket):
        """Test connecting a new client"""
        manager = ConnectionManager()

        await manager.connect(mock_websocket, "client-1")

        assert manager.get_connection_count() == 1
        assert "client-1" in manager.active_connections
        assert "client-1" in manager.connection_metadata
        mock_websocket.accept.assert_called_once()

    async def test_connect_multiple_clients(self, mock_websocket):
        """Test connecting multiple clients"""
        manager = ConnectionManager()
        ws1 = AsyncMock(spec=WebSocket)
        ws2 = AsyncMock(spec=WebSocket)

        await manager.connect(ws1, "client-1")
        await manager.connect(ws2, "client-2")

        assert manager.get_connection_count() == 2

    async def test_disconnect_client(self, mock_websocket):
        """Test disconnecting a client"""
        manager = ConnectionManager()

        await manager.connect(mock_websocket, "client-1")
        await manager.disconnect("client-1")

        assert manager.get_connection_count() == 0
        assert "client-1" not in manager.active_connections

    async def test_disconnect_nonexistent_client(self):
        """Test disconnecting a client that doesn't exist"""
        manager = ConnectionManager()

        # Should not raise error
        await manager.disconnect("nonexistent")

        assert manager.get_connection_count() == 0


@pytest.mark.asyncio
class TestConnectionManagerMessaging:
    """Test message sending functionality"""

    async def test_send_personal_message(self, mock_websocket):
        """Test sending message to specific client"""
        manager = ConnectionManager()
        await manager.connect(mock_websocket, "client-1")

        message = {"type": "test", "data": "hello"}
        await manager.send_personal_message(message, "client-1")

        mock_websocket.send_json.assert_called_once_with(message)

        metadata = manager.get_client_metadata("client-1")
        assert metadata["messages_sent"] == 1

    async def test_send_personal_message_to_nonexistent(self):
        """Test sending message to nonexistent client"""
        manager = ConnectionManager()

        message = {"type": "test"}
        # Should not raise error
        await manager.send_personal_message(message, "nonexistent")

    async def test_send_personal_message_with_error(self, mock_websocket):
        """Test sending message with WebSocket error"""
        manager = ConnectionManager()
        await manager.connect(mock_websocket, "client-1")

        mock_websocket.send_json.side_effect = Exception("Send error")

        message = {"type": "test"}
        await manager.send_personal_message(message, "client-1")

        # Client should be disconnected after error
        assert manager.get_connection_count() == 0

    async def test_broadcast_to_all(self):
        """Test broadcasting to all clients"""
        manager = ConnectionManager()

        ws1 = AsyncMock(spec=WebSocket)
        ws2 = AsyncMock(spec=WebSocket)

        await manager.connect(ws1, "client-1")
        await manager.connect(ws2, "client-2")

        message = {"type": "broadcast", "data": "hello all"}
        await manager.broadcast(message)

        ws1.send_json.assert_called_once_with(message)
        ws2.send_json.assert_called_once_with(message)

    async def test_broadcast_with_exclude(self):
        """Test broadcasting with excluded clients"""
        manager = ConnectionManager()

        ws1 = AsyncMock(spec=WebSocket)
        ws2 = AsyncMock(spec=WebSocket)

        await manager.connect(ws1, "client-1")
        await manager.connect(ws2, "client-2")

        message = {"type": "broadcast"}
        await manager.broadcast(message, exclude={"client-1"})

        ws1.send_json.assert_not_called()
        ws2.send_json.assert_called_once_with(message)

    async def test_broadcast_with_error(self):
        """Test broadcasting with WebSocket error"""
        manager = ConnectionManager()

        ws1 = AsyncMock(spec=WebSocket)
        ws2 = AsyncMock(spec=WebSocket)
        ws1.send_json.side_effect = Exception("Send error")

        await manager.connect(ws1, "client-1")
        await manager.connect(ws2, "client-2")

        message = {"type": "broadcast"}
        await manager.broadcast(message)

        # Client 1 should be disconnected, client 2 should remain
        assert manager.get_connection_count() == 1
        assert "client-2" in manager.active_connections


@pytest.mark.asyncio
class TestConnectionManagerMetadata:
    """Test connection metadata tracking"""

    async def test_get_client_metadata(self, mock_websocket):
        """Test getting client metadata"""
        manager = ConnectionManager()
        await manager.connect(mock_websocket, "client-1")

        metadata = manager.get_client_metadata("client-1")

        assert "connected_at" in metadata
        assert metadata["messages_sent"] == 0
        assert metadata["messages_received"] == 0

    async def test_get_nonexistent_client_metadata(self):
        """Test getting metadata for nonexistent client"""
        manager = ConnectionManager()

        metadata = manager.get_client_metadata("nonexistent")

        assert metadata == {}

    async def test_handle_message_updates_metadata(self, mock_websocket):
        """Test that handling message updates metadata"""
        manager = ConnectionManager()
        await manager.connect(mock_websocket, "client-1")

        await manager.handle_message("client-1", {"type": "test"})

        metadata = manager.get_client_metadata("client-1")
        assert metadata["messages_received"] == 1

    async def test_message_counters(self, mock_websocket):
        """Test message sent/received counters"""
        manager = ConnectionManager()
        await manager.connect(mock_websocket, "client-1")

        # Send messages
        await manager.send_personal_message({"type": "test"}, "client-1")
        await manager.send_personal_message({"type": "test"}, "client-1")

        # Receive messages
        await manager.handle_message("client-1", {"type": "test"})

        metadata = manager.get_client_metadata("client-1")
        assert metadata["messages_sent"] == 2
        assert metadata["messages_received"] == 1


class TestConnectionManagerEdgeCases:
    """Test edge cases"""

    @pytest.mark.asyncio
    async def test_concurrent_connections(self):
        """Test handling concurrent connections"""
        manager = ConnectionManager()

        async def connect_client(client_id):
            ws = AsyncMock(spec=WebSocket)
            await manager.connect(ws, client_id)

        # Connect 10 clients concurrently
        await asyncio.gather(*[connect_client(f"client-{i}") for i in range(10)])

        assert manager.get_connection_count() == 10

    @pytest.mark.asyncio
    async def test_concurrent_disconnections(self):
        """Test handling concurrent disconnections"""
        manager = ConnectionManager()

        # Connect clients
        for i in range(10):
            ws = AsyncMock(spec=WebSocket)
            await manager.connect(ws, f"client-{i}")

        # Disconnect concurrently
        await asyncio.gather(*[manager.disconnect(f"client-{i}") for i in range(10)])

        assert manager.get_connection_count() == 0
