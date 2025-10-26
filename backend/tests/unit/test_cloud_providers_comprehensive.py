"""
Comprehensive tests for Cloud LLM Providers - Targeting 70%+ coverage
Project Creator: Herman Swanepoel

Coverage targets:
- OpenAI provider initialization and generation
- Anthropic provider initialization and generation
- Content extraction from API responses
- Privacy Manager sanitization and validation
- Error handling and edge cases
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from src.services.cloud_providers import (
    AnthropicProvider,
    CloudProviderError,
    OpenAIProvider,
    PrivacyManager,
    ProviderConfigurationError,
    ProviderDependencyError,
)


class TestOpenAIProviderComprehensive:
    """Comprehensive tests for OpenAI provider"""

    def test_initialization(self):
        """Test OpenAI provider initialization"""
        provider = OpenAIProvider(api_key="test-key", model="gpt-4")

        assert provider.api_key == "test-key"
        assert provider.model == "gpt-4"
        assert provider._client is None
        assert provider._client_mode is None

    def test_client_ready_when_not_initialized(self):
        """Test _client_ready returns False when client not initialized"""
        provider = OpenAIProvider(api_key="test-key", model="gpt-4")

        assert provider._client_ready() is False

    def test_client_ready_when_initialized(self):
        """Test _client_ready returns True when client initialized"""
        provider = OpenAIProvider(api_key="test-key", model="gpt-4")
        provider._client = Mock()

        assert provider._client_ready() is True

    def test_ensure_client_missing_api_key(self):
        """Test _ensure_client raises error when API key is missing"""
        provider = OpenAIProvider(api_key="", model="gpt-4")

        with pytest.raises(ProviderConfigurationError) as exc_info:
            provider._ensure_client()

        assert "requires an API key" in str(exc_info.value)

    @patch("src.services.cloud_providers.importlib.import_module")
    def test_ensure_client_async_client(self, mock_import):
        """Test _ensure_client with AsyncOpenAI client"""
        mock_module = Mock()
        mock_async_client = Mock()
        mock_module.AsyncOpenAI = mock_async_client
        mock_import.return_value = mock_module

        provider = OpenAIProvider(api_key="test-key", model="gpt-4")
        provider._ensure_client()

        assert provider._client_mode == "async"
        assert provider._client is not None
        mock_async_client.assert_called_once_with(api_key="test-key")

    @patch("src.services.cloud_providers.importlib.import_module")
    def test_ensure_client_sync_client(self, mock_import):
        """Test _ensure_client with sync OpenAI client"""
        mock_module = Mock()
        mock_module.AsyncOpenAI = None
        mock_sync_client = Mock()
        mock_module.OpenAI = mock_sync_client
        mock_import.return_value = mock_module

        provider = OpenAIProvider(api_key="test-key", model="gpt-4")
        provider._ensure_client()

        assert provider._client_mode == "sync"
        assert provider._client is not None
        mock_sync_client.assert_called_once_with(api_key="test-key")

    @patch("src.services.cloud_providers.importlib.import_module")
    def test_ensure_client_legacy_client(self, mock_import):
        """Test _ensure_client with legacy ChatCompletion"""
        mock_module = Mock()
        mock_module.AsyncOpenAI = None
        mock_module.OpenAI = None
        mock_module.ChatCompletion = Mock()
        mock_import.return_value = mock_module

        provider = OpenAIProvider(api_key="test-key", model="gpt-4")
        provider._ensure_client()

        assert provider._client_mode == "legacy"
        assert provider._client is not None
        assert mock_module.api_key == "test-key"

    def test_extract_content_with_message_content(self):
        """Test _extract_content with standard message content"""
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = "Test response"
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        result = OpenAIProvider._extract_content(mock_response)

        assert result == "Test response"

    def test_extract_content_with_text_field(self):
        """Test _extract_content with text field"""
        mock_response = Mock()
        mock_choice = Mock()
        mock_choice.message = None
        mock_choice.text = "  Test text  "
        mock_response.choices = [mock_choice]

        result = OpenAIProvider._extract_content(mock_response)

        assert result == "Test text"

    def test_extract_content_with_dict_response(self):
        """Test _extract_content with dictionary response"""
        response = {"choices": [{"message": {"content": "Dictionary response"}}]}

        result = OpenAIProvider._extract_content(response)

        assert result == "Dictionary response"

    def test_extract_content_with_list_content(self):
        """Test _extract_content with list content"""
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()

        # Content as list of text parts
        content_parts = [
            Mock(text="Part 1 "),
            Mock(text="Part 2"),
        ]
        mock_message.content = content_parts
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        result = OpenAIProvider._extract_content(mock_response)

        assert result == "Part 1 Part 2"

    def test_extract_content_no_choices(self):
        """Test _extract_content raises error when no choices"""
        mock_response = Mock()
        mock_response.choices = []

        with pytest.raises(CloudProviderError) as exc_info:
            OpenAIProvider._extract_content(mock_response)

        assert "did not include any choices" in str(exc_info.value)

    def test_extract_content_empty_content(self):
        """Test _extract_content raises error when content is empty"""
        mock_response = Mock()
        mock_choice = Mock()
        mock_message = Mock()
        mock_message.content = ""
        mock_choice.message = mock_message
        mock_response.choices = [mock_choice]

        with pytest.raises(CloudProviderError) as exc_info:
            OpenAIProvider._extract_content(mock_response)

        assert "content was empty" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("src.services.cloud_providers.importlib.import_module")
    async def test_generate_async_client(self, mock_import):
        """Test generate with async client"""
        mock_module = Mock()
        mock_client_instance = Mock()
        mock_client_instance.chat.completions.create = AsyncMock(
            return_value=Mock(choices=[Mock(message=Mock(content="Generated text"))])
        )
        mock_module.AsyncOpenAI = Mock(return_value=mock_client_instance)
        mock_import.return_value = mock_module

        provider = OpenAIProvider(api_key="test-key", model="gpt-4")
        result = await provider.generate("Test prompt")

        assert result == "Generated text"
        mock_client_instance.chat.completions.create.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.cloud_providers.importlib.import_module")
    async def test_generate_with_system_prompt(self, mock_import):
        """Test generate with system prompt"""
        mock_module = Mock()
        mock_client_instance = Mock()
        mock_client_instance.chat.completions.create = AsyncMock(
            return_value=Mock(choices=[Mock(message=Mock(content="Response with system"))])
        )
        mock_module.AsyncOpenAI = Mock(return_value=mock_client_instance)
        mock_import.return_value = mock_module

        provider = OpenAIProvider(api_key="test-key", model="gpt-4")
        result = await provider.generate("User prompt", system_prompt="System instructions")

        assert result == "Response with system"
        call_args = mock_client_instance.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert len(messages) == 2
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"

    @pytest.mark.asyncio
    @patch("src.services.cloud_providers.importlib.import_module")
    async def test_generate_with_max_tokens(self, mock_import):
        """Test generate with max_tokens parameter"""
        mock_module = Mock()
        mock_client_instance = Mock()
        mock_client_instance.chat.completions.create = AsyncMock(
            return_value=Mock(choices=[Mock(message=Mock(content="Limited response"))])
        )
        mock_module.AsyncOpenAI = Mock(return_value=mock_client_instance)
        mock_import.return_value = mock_module

        provider = OpenAIProvider(api_key="test-key", model="gpt-4")
        result = await provider.generate("Prompt", max_tokens=100)

        assert result == "Limited response"
        call_args = mock_client_instance.chat.completions.create.call_args
        assert call_args.kwargs["max_tokens"] == 100

    @pytest.mark.asyncio
    @patch("src.services.cloud_providers.importlib.import_module")
    async def test_generate_with_stop_sequences(self, mock_import):
        """Test generate with stop sequences"""
        mock_module = Mock()
        mock_client_instance = Mock()
        mock_client_instance.chat.completions.create = AsyncMock(
            return_value=Mock(choices=[Mock(message=Mock(content="Stopped text"))])
        )
        mock_module.AsyncOpenAI = Mock(return_value=mock_client_instance)
        mock_import.return_value = mock_module

        provider = OpenAIProvider(api_key="test-key", model="gpt-4")
        result = await provider.generate("Prompt", stop=["STOP", "END"])

        assert result == "Stopped text"
        call_args = mock_client_instance.chat.completions.create.call_args
        assert call_args.kwargs["stop"] == ["STOP", "END"]

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test health_check returns True when client can be ensured"""
        provider = OpenAIProvider(api_key="test-key", model="gpt-4")

        with patch.object(provider, "_ensure_client", return_value=Mock()):
            result = await provider.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health_check returns False on CloudProviderError"""
        provider = OpenAIProvider(api_key="", model="gpt-4")

        result = await provider.health_check()

        assert result is False


class TestAnthropicProviderComprehensive:
    """Comprehensive tests for Anthropic provider"""

    def test_initialization(self):
        """Test Anthropic provider initialization"""
        provider = AnthropicProvider(api_key="test-key", model="claude-3")

        assert provider.api_key == "test-key"
        assert provider.model == "claude-3"
        assert provider._client is None
        assert provider._client_mode is None

    def test_client_ready(self):
        """Test _client_ready method"""
        provider = AnthropicProvider(api_key="test-key", model="claude-3")

        assert provider._client_ready() is False

        provider._client = Mock()
        assert provider._client_ready() is True

    def test_ensure_client_missing_api_key(self):
        """Test _ensure_client raises error when API key is missing"""
        provider = AnthropicProvider(api_key="", model="claude-3")

        with pytest.raises(ProviderConfigurationError) as exc_info:
            provider._ensure_client()

        assert "requires an API key" in str(exc_info.value)

    @patch("src.services.cloud_providers.importlib.import_module")
    def test_ensure_client_async_client(self, mock_import):
        """Test _ensure_client with AsyncAnthropic client"""
        mock_module = Mock()
        mock_async_client = Mock()
        mock_module.AsyncAnthropic = mock_async_client
        mock_import.return_value = mock_module

        provider = AnthropicProvider(api_key="test-key", model="claude-3")
        provider._ensure_client()

        assert provider._client_mode == "async"
        assert provider._client is not None
        mock_async_client.assert_called_once_with(api_key="test-key")

    @patch("src.services.cloud_providers.importlib.import_module")
    def test_ensure_client_sync_client(self, mock_import):
        """Test _ensure_client with sync Anthropic client"""
        mock_module = Mock()
        mock_module.AsyncAnthropic = None
        mock_sync_client = Mock()
        mock_module.Anthropic = mock_sync_client
        mock_import.return_value = mock_module

        provider = AnthropicProvider(api_key="test-key", model="claude-3")
        provider._ensure_client()

        assert provider._client_mode == "sync"
        assert provider._client is not None
        mock_sync_client.assert_called_once_with(api_key="test-key")

    def test_extract_content_with_list_content(self):
        """Test _extract_content with list content"""
        mock_response = Mock()
        content_parts = [
            Mock(text="Part 1 "),
            Mock(text="Part 2"),
        ]
        mock_response.content = content_parts

        result = AnthropicProvider._extract_content(mock_response)

        assert result == "Part 1 Part 2"

    def test_extract_content_with_completion_field(self):
        """Test _extract_content with completion field"""
        mock_response = Mock()
        mock_response.content = None
        mock_response.completion = "  Completion text  "

        result = AnthropicProvider._extract_content(mock_response)

        assert result == "Completion text"

    def test_extract_content_with_dict_completion(self):
        """Test _extract_content with dictionary completion"""
        response = {"completion": "Dictionary completion"}

        result = AnthropicProvider._extract_content(response)

        assert result == "Dictionary completion"

    def test_extract_content_with_dict_content_blocks(self):
        """Test _extract_content with dictionary content blocks"""
        response = {
            "content": [
                {"text": "Block 1 "},
                {"text": "Block 2"},
            ]
        }

        result = AnthropicProvider._extract_content(response)

        assert result == "Block 1 Block 2"

    def test_extract_content_empty_raises_error(self):
        """Test _extract_content raises error when content is empty"""
        mock_response = Mock()
        mock_response.content = []
        mock_response.completion = None

        with pytest.raises(CloudProviderError) as exc_info:
            AnthropicProvider._extract_content(mock_response)

        assert "content was empty" in str(exc_info.value)

    @pytest.mark.asyncio
    @patch("src.services.cloud_providers.importlib.import_module")
    async def test_generate_async_client(self, mock_import):
        """Test generate with async client"""
        mock_module = Mock()
        mock_client_instance = Mock()
        mock_client_instance.messages.create = AsyncMock(
            return_value=Mock(content=[Mock(text="Generated from Claude")])
        )
        mock_module.AsyncAnthropic = Mock(return_value=mock_client_instance)
        mock_import.return_value = mock_module

        provider = AnthropicProvider(api_key="test-key", model="claude-3")
        result = await provider.generate("Test prompt")

        assert result == "Generated from Claude"
        mock_client_instance.messages.create.assert_called_once()

    @pytest.mark.asyncio
    @patch("src.services.cloud_providers.importlib.import_module")
    async def test_generate_with_system_prompt(self, mock_import):
        """Test generate with system prompt"""
        mock_module = Mock()
        mock_client_instance = Mock()
        mock_client_instance.messages.create = AsyncMock(
            return_value=Mock(content=[Mock(text="System response")])
        )
        mock_module.AsyncAnthropic = Mock(return_value=mock_client_instance)
        mock_import.return_value = mock_module

        provider = AnthropicProvider(api_key="test-key", model="claude-3")
        result = await provider.generate("User prompt", system_prompt="System instructions")

        assert result == "System response"
        call_args = mock_client_instance.messages.create.call_args
        assert "system" in call_args.kwargs
        assert call_args.kwargs["system"] == "System instructions"

    @pytest.mark.asyncio
    @patch("src.services.cloud_providers.importlib.import_module")
    async def test_generate_with_max_tokens(self, mock_import):
        """Test generate with custom max_tokens"""
        mock_module = Mock()
        mock_client_instance = Mock()
        mock_client_instance.messages.create = AsyncMock(
            return_value=Mock(content=[Mock(text="Limited")])
        )
        mock_module.AsyncAnthropic = Mock(return_value=mock_client_instance)
        mock_import.return_value = mock_module

        provider = AnthropicProvider(api_key="test-key", model="claude-3")
        result = await provider.generate("Prompt", max_tokens=500)

        assert result == "Limited"
        call_args = mock_client_instance.messages.create.call_args
        assert call_args.kwargs["max_tokens"] == 500

    @pytest.mark.asyncio
    @patch("src.services.cloud_providers.importlib.import_module")
    async def test_generate_uses_default_max_tokens(self, mock_import):
        """Test generate uses DEFAULT_MAX_TOKENS when not specified"""
        mock_module = Mock()
        mock_client_instance = Mock()
        mock_client_instance.messages.create = AsyncMock(
            return_value=Mock(content=[Mock(text="Default")])
        )
        mock_module.AsyncAnthropic = Mock(return_value=mock_client_instance)
        mock_import.return_value = mock_module

        provider = AnthropicProvider(api_key="test-key", model="claude-3")
        result = await provider.generate("Prompt")

        assert result == "Default"
        call_args = mock_client_instance.messages.create.call_args
        assert call_args.kwargs["max_tokens"] == provider.DEFAULT_MAX_TOKENS

    @pytest.mark.asyncio
    @patch("src.services.cloud_providers.importlib.import_module")
    async def test_generate_with_stop_sequences(self, mock_import):
        """Test generate with stop sequences"""
        mock_module = Mock()
        mock_client_instance = Mock()
        mock_client_instance.messages.create = AsyncMock(
            return_value=Mock(content=[Mock(text="Stopped")])
        )
        mock_module.AsyncAnthropic = Mock(return_value=mock_client_instance)
        mock_import.return_value = mock_module

        provider = AnthropicProvider(api_key="test-key", model="claude-3")
        result = await provider.generate("Prompt", stop=["STOP"])

        assert result == "Stopped"
        call_args = mock_client_instance.messages.create.call_args
        assert call_args.kwargs["stop_sequences"] == ["STOP"]

    @pytest.mark.asyncio
    async def test_health_check_success(self):
        """Test health_check returns True when client can be ensured"""
        provider = AnthropicProvider(api_key="test-key", model="claude-3")

        with patch.object(provider, "_ensure_client", return_value=Mock()):
            result = await provider.health_check()

        assert result is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self):
        """Test health_check returns False on CloudProviderError"""
        provider = AnthropicProvider(api_key="", model="claude-3")

        result = await provider.health_check()

        assert result is False


class TestPrivacyManagerComprehensive:
    """Comprehensive tests for PrivacyManager"""

    def test_initialization_default(self):
        """Test PrivacyManager initialization with defaults"""
        manager = PrivacyManager()

        assert manager.allow_cloud is False
        assert len(manager.sensitive_patterns) > 0

    def test_initialization_allow_cloud(self):
        """Test PrivacyManager initialization with cloud enabled"""
        manager = PrivacyManager(allow_cloud=True)

        assert manager.allow_cloud is True

    def test_can_use_cloud_when_disabled(self):
        """Test can_use_cloud returns False when cloud disabled"""
        manager = PrivacyManager(allow_cloud=False)

        allowed, reason = manager.can_use_cloud("def hello(): pass")

        assert allowed is False
        assert reason == "Cloud usage disabled"

    def test_can_use_cloud_with_email(self):
        """Test can_use_cloud detects email addresses"""
        manager = PrivacyManager(allow_cloud=True)

        code = "email = 'user@example.com'"
        allowed, reason = manager.can_use_cloud(code)

        assert allowed is False
        assert "sensitive data" in reason

    def test_can_use_cloud_with_phone(self):
        """Test can_use_cloud detects phone numbers"""
        manager = PrivacyManager(allow_cloud=True)

        code = "phone = '555-123-4567'"
        allowed, reason = manager.can_use_cloud(code)

        assert allowed is False
        assert "sensitive data" in reason

    def test_can_use_cloud_with_ssn(self):
        """Test can_use_cloud detects SSN"""
        manager = PrivacyManager(allow_cloud=True)

        code = "ssn = '123-45-6789'"
        allowed, reason = manager.can_use_cloud(code)

        assert allowed is False
        assert "sensitive data" in reason

    def test_can_use_cloud_with_password(self):
        """Test can_use_cloud detects password"""
        manager = PrivacyManager(allow_cloud=True)

        code = "password = 'secretpass123'"
        allowed, reason = manager.can_use_cloud(code)

        assert allowed is False
        assert "sensitive data" in reason

    def test_can_use_cloud_with_api_key(self):
        """Test can_use_cloud detects API keys"""
        manager = PrivacyManager(allow_cloud=True)

        code = "api_key = 'sk-" + "a" * 48 + "'"
        allowed, reason = manager.can_use_cloud(code)

        assert allowed is False
        assert "sensitive data" in reason

    def test_can_use_cloud_clean_code(self):
        """Test can_use_cloud allows clean code"""
        manager = PrivacyManager(allow_cloud=True)

        code = """
def calculate(x, y):
    return x + y
"""
        allowed, reason = manager.can_use_cloud(code)

        assert allowed is True
        assert reason is None

    def test_sanitize_code_email(self):
        """Test sanitize_code redacts email addresses"""
        manager = PrivacyManager()

        code = "email = 'test@example.com'"
        sanitized = manager.sanitize_code(code)

        assert "[EMAIL_REDACTED]" in sanitized
        assert "test@example.com" not in sanitized

    def test_sanitize_code_phone(self):
        """Test sanitize_code redacts phone numbers"""
        manager = PrivacyManager()

        code = "phone = '555-123-4567'"
        sanitized = manager.sanitize_code(code)

        assert "[PHONE_REDACTED]" in sanitized
        assert "555-123-4567" not in sanitized

    def test_sanitize_code_ssn(self):
        """Test sanitize_code redacts SSN"""
        manager = PrivacyManager()

        code = "ssn = '123-45-6789'"
        sanitized = manager.sanitize_code(code)

        assert "[SSN_REDACTED]" in sanitized
        assert "123-45-6789" not in sanitized

    def test_sanitize_code_password(self):
        """Test sanitize_code redacts passwords"""
        manager = PrivacyManager()

        code = "password = 'mypassword123'"
        sanitized = manager.sanitize_code(code)

        assert "[REDACTED]" in sanitized
        assert "mypassword123" not in sanitized

    def test_sanitize_code_api_key(self):
        """Test sanitize_code redacts API keys"""
        manager = PrivacyManager()

        code = "key = 'sk-" + "a" * 48 + "'"
        sanitized = manager.sanitize_code(code)

        # API keys are caught by the secret/key pattern and redacted generically
        assert "[REDACTED]" in sanitized
        assert "sk-" + "a" * 48 not in sanitized

    def test_sanitize_code_multiple_patterns(self):
        """Test sanitize_code handles multiple sensitive patterns"""
        manager = PrivacyManager()

        code = """
email = 'user@example.com'
phone = '555-123-4567'
password = 'secret123'
"""
        sanitized = manager.sanitize_code(code)

        assert "[EMAIL_REDACTED]" in sanitized
        assert "[PHONE_REDACTED]" in sanitized
        assert "[REDACTED]" in sanitized
        assert "user@example.com" not in sanitized
        assert "555-123-4567" not in sanitized
        assert "secret123" not in sanitized

    def test_sanitize_code_preserves_clean_code(self):
        """Test sanitize_code preserves code without sensitive data"""
        manager = PrivacyManager()

        code = """
def hello():
    return "world"
"""
        sanitized = manager.sanitize_code(code)

        assert sanitized == code


class TestExceptionsComprehensive:
    """Test exception hierarchy"""

    def test_cloud_provider_error_inheritance(self):
        """Test CloudProviderError inherits from Exception"""
        assert issubclass(CloudProviderError, Exception)

    def test_provider_configuration_error_inheritance(self):
        """Test ProviderConfigurationError inherits from CloudProviderError"""
        assert issubclass(ProviderConfigurationError, CloudProviderError)

    def test_provider_dependency_error_inheritance(self):
        """Test ProviderDependencyError inherits from CloudProviderError"""
        assert issubclass(ProviderDependencyError, CloudProviderError)

    def test_raise_cloud_provider_error(self):
        """Test raising CloudProviderError"""
        with pytest.raises(CloudProviderError) as exc_info:
            raise CloudProviderError("Test error")

        assert "Test error" in str(exc_info.value)

    def test_raise_provider_configuration_error(self):
        """Test raising ProviderConfigurationError"""
        with pytest.raises(ProviderConfigurationError) as exc_info:
            raise ProviderConfigurationError("Config error")

        assert "Config error" in str(exc_info.value)

    def test_raise_provider_dependency_error(self):
        """Test raising ProviderDependencyError"""
        with pytest.raises(ProviderDependencyError) as exc_info:
            raise ProviderDependencyError("Dependency error")

        assert "Dependency error" in str(exc_info.value)


class TestEdgeCasesComprehensive:
    """Test edge cases and error handling"""

    def test_openai_extract_content_dict_with_text(self):
        """Test OpenAI content extraction with dict containing text"""
        response = {"choices": [{"text": "Dict text"}]}

        result = OpenAIProvider._extract_content(response)

        assert result == "Dict text"

    def test_anthropic_extract_content_dict_items(self):
        """Test Anthropic content extraction with dict items"""
        response = {"content": [{"text": "Item 1"}, {"text": "Item 2"}]}

        result = AnthropicProvider._extract_content(response)

        assert result == "Item 1Item 2"

    def test_privacy_manager_case_insensitive_password(self):
        """Test PrivacyManager detects password case-insensitively"""
        manager = PrivacyManager(allow_cloud=True)

        code = "PASSWORD = 'secret'"
        allowed, reason = manager.can_use_cloud(code)

        assert allowed is False

    def test_privacy_manager_token_pattern(self):
        """Test PrivacyManager detects token pattern"""
        manager = PrivacyManager(allow_cloud=True)

        code = "token = 'abc123xyz'"
        allowed, reason = manager.can_use_cloud(code)

        assert allowed is False

    def test_privacy_manager_secret_pattern(self):
        """Test PrivacyManager detects secret pattern"""
        manager = PrivacyManager(allow_cloud=True)

        code = "secret: mysecret"
        allowed, reason = manager.can_use_cloud(code)

        assert allowed is False

    @pytest.mark.asyncio
    async def test_openai_generate_with_temperature(self):
        """Test OpenAI generate respects temperature parameter"""
        provider = OpenAIProvider(api_key="test-key", model="gpt-4")

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = Mock()
            mock_client.chat.completions.create = AsyncMock(
                return_value=Mock(choices=[Mock(message=Mock(content="Response"))])
            )
            mock_ensure.return_value = mock_client
            provider._client_mode = "async"

            result = await provider.generate("Test", temperature=0.5)

            assert result == "Response"
            call_args = mock_client.chat.completions.create.call_args
            assert call_args.kwargs["temperature"] == 0.5

    @pytest.mark.asyncio
    async def test_anthropic_generate_with_temperature(self):
        """Test Anthropic generate respects temperature parameter"""
        provider = AnthropicProvider(api_key="test-key", model="claude-3")

        with patch.object(provider, "_ensure_client") as mock_ensure:
            mock_client = Mock()
            mock_client.messages.create = AsyncMock(
                return_value=Mock(content=[Mock(text="Response")])
            )
            mock_ensure.return_value = mock_client
            provider._client_mode = "async"

            result = await provider.generate("Test", temperature=0.9)

            assert result == "Response"
            call_args = mock_client.messages.create.call_args
            assert call_args.kwargs["temperature"] == 0.9
            assert call_args.kwargs["temperature"] == 0.9
