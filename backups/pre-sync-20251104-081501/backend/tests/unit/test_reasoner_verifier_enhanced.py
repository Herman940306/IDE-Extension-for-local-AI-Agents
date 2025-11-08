"""
Enhanced tests for FastReasoner and AnalyticalVerifier models
Project Creator: Herman Swanepoel
"""

from unittest.mock import AsyncMock, Mock, patch

import httpx
import pytest
from src.models.reasoner import FastReasoner, ReasoningRequest, ReasoningResponse
from src.models.verifier import (
    AnalyticalVerifier,
    VerificationRequest,
    VerificationResponse,
)


class TestFastReasoner:
    """Test FastReasoner (System 1)"""

    @pytest.fixture
    def reasoner(self):
        """Create FastReasoner instance"""
        return FastReasoner(
            ollama_url="http://localhost:11434", model="llama3.2:3b", timeout=30.0
        )

    def test_initialization(self, reasoner):
        """Test FastReasoner initialization"""
        assert reasoner.ollama_url == "http://localhost:11434"
        assert reasoner.model == "llama3.2:3b"
        assert reasoner.timeout == 30.0
        assert reasoner.total_requests == 0
        assert reasoner.total_latency == 0.0
        assert reasoner.cache_hits == 0

    def test_build_prompt_basic(self, reasoner):
        """Test basic prompt building"""
        request = ReasoningRequest(
            task_type="refactor",
            description="Improve code quality",
            code_context="def foo():\n    pass",
            language="python",
        )

        prompt = reasoner._build_prompt(request)

        assert "Task: refactor" in prompt
        assert "Improve code quality" in prompt
        assert "Language: python" in prompt
        assert "def foo():" in prompt
        assert "Suggestion:" in prompt

    def test_build_prompt_with_selection(self, reasoner):
        """Test prompt building with selected text"""
        request = ReasoningRequest(
            task_type="fix",
            description="Fix bug",
            code_context="def foo():\n    x = 1\n    return x",
            language="python",
            selected_text="x = 1",
        )

        prompt = reasoner._build_prompt(request)

        assert "x = 1" in prompt
        assert "Focus on this specific code:" in prompt
        assert "def foo():" in prompt

    def test_parse_suggestions_with_code_blocks(self, reasoner):
        """Test parsing suggestions with code blocks"""
        response = {
            "text": "Here's a fix:\n```python\ndef foo():\n    return 42\n```\n",
            "reasoning": "test",
        }

        suggestions = reasoner._parse_suggestions(response)

        assert len(suggestions) == 1
        assert "def foo():" in suggestions[0]
        assert "return 42" in suggestions[0]

    def test_parse_suggestions_multiple_blocks(self, reasoner):
        """Test parsing multiple code blocks"""
        response = {
            "text": "```python\nx = 1\n```\nAnd also:\n```python\ny = 2\n```",
            "reasoning": "test",
        }

        suggestions = reasoner._parse_suggestions(response)

        assert len(suggestions) == 2
        assert "x = 1" in suggestions[0]
        assert "y = 2" in suggestions[1]

    def test_parse_suggestions_no_code_blocks(self, reasoner):
        """Test parsing when no code blocks present"""
        response = {
            "text": "You should refactor this function to be more modular.",
            "reasoning": "test",
        }

        suggestions = reasoner._parse_suggestions(response)

        assert len(suggestions) == 1
        assert "refactor" in suggestions[0]

    def test_parse_suggestions_empty_response(self, reasoner):
        """Test parsing empty response"""
        response = {"text": "", "reasoning": "test"}

        suggestions = reasoner._parse_suggestions(response)

        assert suggestions == []

    def test_calculate_confidence_simple_task(self, reasoner):
        """Test confidence calculation for simple tasks"""
        response = {"text": "```python\ncode here\n```"}
        request = ReasoningRequest(
            task_type="explain",
            description="test",
            code_context="code",
            language="python",
        )

        confidence = reasoner._calculate_confidence(response, request)

        assert 0.0 <= confidence <= 1.0
        assert confidence >= 0.8  # Simple task + code blocks

    def test_calculate_confidence_complex_task(self, reasoner):
        """Test confidence calculation for complex tasks"""
        response = {"text": "Here's a suggestion"}
        request = ReasoningRequest(
            task_type="refactor",
            description="test",
            code_context="code",
            language="python",
        )

        confidence = reasoner._calculate_confidence(response, request)

        assert 0.0 <= confidence <= 1.0
        assert confidence < 0.75  # Complex task without code

    def test_calculate_confidence_with_code_blocks(self, reasoner):
        """Test confidence boost with code blocks"""
        response_with_code = {"text": "```python\ncode\n```"}
        response_without_code = {"text": "text only"}
        request = ReasoningRequest(
            task_type="comment",
            description="test",
            code_context="code",
            language="python",
        )

        conf_with = reasoner._calculate_confidence(response_with_code, request)
        conf_without = reasoner._calculate_confidence(response_without_code, request)

        assert conf_with > conf_without

    @pytest.mark.asyncio
    async def test_reason_success(self, reasoner):
        """Test successful reasoning"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "```python\ndef improved():\n    return True\n```"
        }
        mock_response.raise_for_status = Mock()

        reasoner.client.post = AsyncMock(return_value=mock_response)

        request = ReasoningRequest(
            task_type="refactor",
            description="Improve function",
            code_context="def foo(): pass",
            language="python",
        )

        result = await reasoner.reason(request)

        assert isinstance(result, ReasoningResponse)
        assert len(result.suggestions) > 0
        assert result.confidence > 0
        assert result.latency_ms > 0
        assert result.model == "llama3.2:3b"
        assert reasoner.total_requests == 1
        assert reasoner.total_latency > 0

    @pytest.mark.asyncio
    async def test_reason_failure(self, reasoner):
        """Test reasoning with API failure"""
        reasoner.client.post = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )

        request = ReasoningRequest(
            task_type="refactor",
            description="Test",
            code_context="code",
            language="python",
        )

        result = await reasoner.reason(request)

        assert isinstance(result, ReasoningResponse)
        assert result.suggestions == []
        assert result.confidence == 0.0
        assert "failed" in result.reasoning.lower()
        assert result.latency_ms >= 0  # Can be 0 on very fast failures

    @pytest.mark.asyncio
    async def test_call_ollama_success(self, reasoner):
        """Test successful Ollama API call"""
        with patch("src.models.reasoner.get_settings") as mock_settings:
            mock_settings.return_value.ollama_max_retries = 2
            mock_settings.return_value.ollama_retry_backoff_seconds = 0.01
            mock_settings.return_value.reasoner_keep_alive = "30m"

            mock_response = Mock()
            mock_response.json.return_value = {"response": "test response"}
            mock_response.raise_for_status = Mock()

            reasoner.client.post = AsyncMock(return_value=mock_response)

            result = await reasoner._call_ollama("test prompt")

            assert result["text"] == "test response"
            assert "reasoning" in result

    @pytest.mark.asyncio
    async def test_call_ollama_retry_on_timeout(self, reasoner):
        """Test retry logic on timeout"""
        with patch("src.models.reasoner.get_settings") as mock_settings:
            mock_settings.return_value.ollama_max_retries = 2
            mock_settings.return_value.ollama_retry_backoff_seconds = 0.01
            mock_settings.return_value.reasoner_keep_alive = "30m"

            reasoner.client.post = AsyncMock(
                side_effect=httpx.TimeoutException("Timeout")
            )

            with pytest.raises(httpx.TimeoutException):
                await reasoner._call_ollama("test prompt")

    @pytest.mark.asyncio
    async def test_call_ollama_retry_on_5xx_error(self, reasoner):
        """Test retry logic on 5xx HTTP errors"""
        with patch("src.models.reasoner.get_settings") as mock_settings:
            mock_settings.return_value.ollama_max_retries = 2
            mock_settings.return_value.ollama_retry_backoff_seconds = 0.01
            mock_settings.return_value.reasoner_keep_alive = "30m"

            mock_response = Mock()
            mock_response.status_code = 503

            reasoner.client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Server error", request=Mock(), response=mock_response
                )
            )

            with pytest.raises(httpx.HTTPStatusError):
                await reasoner._call_ollama("test prompt")

    @pytest.mark.asyncio
    async def test_call_ollama_no_retry_on_4xx_error(self, reasoner):
        """Test no retry on 4xx HTTP errors"""
        with patch("src.models.reasoner.get_settings") as mock_settings:
            mock_settings.return_value.ollama_max_retries = 2
            mock_settings.return_value.ollama_retry_backoff_seconds = 0.01
            mock_settings.return_value.reasoner_keep_alive = "30m"

            mock_response = Mock()
            mock_response.status_code = 404

            reasoner.client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Not found", request=Mock(), response=mock_response
                )
            )

            with pytest.raises(httpx.HTTPStatusError):
                await reasoner._call_ollama("test prompt")

    def test_get_stats(self, reasoner):
        """Test statistics retrieval"""
        reasoner.total_requests = 10
        reasoner.total_latency = 1000.0
        reasoner.cache_hits = 3

        stats = reasoner.get_stats()

        assert stats["total_requests"] == 10
        assert stats["avg_latency_ms"] == 100.0
        assert stats["cache_hits"] == 3
        assert stats["cache_hit_rate"] == 0.3
        assert stats["model"] == "llama3.2:3b"

    def test_get_stats_no_requests(self, reasoner):
        """Test statistics with no requests"""
        stats = reasoner.get_stats()

        assert stats["total_requests"] == 0
        assert stats["avg_latency_ms"] == 0
        assert stats["cache_hit_rate"] == 0

    @pytest.mark.asyncio
    async def test_close(self, reasoner):
        """Test closing HTTP client"""
        reasoner.client.aclose = AsyncMock()
        await reasoner.close()
        # Called twice in the implementation
        assert reasoner.client.aclose.call_count == 2


class TestAnalyticalVerifier:
    """Test AnalyticalVerifier (System 2)"""

    @pytest.fixture
    def verifier(self):
        """Create AnalyticalVerifier instance"""
        return AnalyticalVerifier(
            ollama_url="http://localhost:11434", model="mistral:7b", timeout=60.0
        )

    def test_initialization(self, verifier):
        """Test AnalyticalVerifier initialization"""
        assert verifier.ollama_url == "http://localhost:11434"
        assert verifier.model == "mistral:7b"
        assert verifier.timeout == 60.0
        assert verifier.total_verifications == 0
        assert verifier.total_latency == 0.0
        assert verifier.rejections == 0

    def test_build_verification_prompt_basic(self, verifier):
        """Test basic verification prompt building"""
        request = VerificationRequest(
            code="def new(): return 42",
            language="python",
            context="refactor task",
            original_task="Improve function",
            system1_confidence=0.8,
        )

        prompt = verifier._build_verification_prompt(request)

        assert "def new(): return 42" in prompt
        assert "Language: python" in prompt
        assert "refactor task" in prompt
        # System1 confidence is not included in the prompt itself

    def test_build_verification_prompt_with_context(self, verifier):
        """Test verification prompt with additional context"""
        request = VerificationRequest(
            code="x = 2",
            language="python",
            context="This is a bug fix for variable assignment",
            original_task="Fix variable assignment",
            system1_confidence=0.75,
        )

        prompt = verifier._build_verification_prompt(request)

        assert "bug fix" in prompt
        assert "x = 2" in prompt
        assert "Fix variable assignment" in prompt

    def test_parse_verification_valid(self, verifier):
        """Test parsing valid verification"""
        response = {
            "text": "VALID: YES\n\nThe refactoring is correct and improves code quality."
        }

        is_valid, issues, suggestions = verifier._parse_verification(response)

        assert is_valid is True
        assert len(issues) == 0

    def test_parse_verification_invalid(self, verifier):
        """Test parsing invalid verification"""
        response = {"text": "VALID: NO\n\nThis change introduces a bug."}

        is_valid, issues, suggestions = verifier._parse_verification(response)

        assert is_valid is False

    def test_parse_verification_with_issues(self, verifier):
        """Test parsing verification with specific issues"""
        response = {
            "text": """VALID: NO

ISSUES:
- Missing error handling
- Performance concern
- Type safety issue

SUGGESTIONS:
- Add try-catch
"""
        }

        is_valid, issues, suggestions = verifier._parse_verification(response)

        assert is_valid is False
        assert len(issues) >= 1
        assert "error handling" in issues[0]["message"].lower()

    def test_parse_verification_with_suggestions(self, verifier):
        """Test parsing verification with suggestions"""
        response = {
            "text": """VALID: YES

SUGGESTIONS:
- Better naming
- More efficient
- Add documentation

REASONING:
Code is correct
"""
        }

        is_valid, issues, suggestions = verifier._parse_verification(response)

        assert is_valid is True
        assert len(suggestions) >= 1
        assert any("naming" in s.lower() for s in suggestions)

    def test_parse_verification_ambiguous(self, verifier):
        """Test parsing ambiguous response defaults to invalid"""
        response = {"text": "This looks okay maybe"}

        is_valid, issues, suggestions = verifier._parse_verification(response)

        assert is_valid is False

    def test_calculate_confidence_valid_high_system1(self, verifier):
        """Test confidence calculation for valid with high System 1 confidence"""
        confidence = verifier._calculate_confidence(
            is_valid=True, issues=[], system1_confidence=0.9
        )

        assert 0.0 <= confidence <= 1.0
        assert confidence > 0.8

    def test_calculate_confidence_invalid_with_issues(self, verifier):
        """Test confidence calculation for invalid with issues"""
        issues = [
            {"type": "error", "message": "Bug 1"},
            {"type": "error", "message": "Bug 2"},
        ]
        confidence = verifier._calculate_confidence(
            is_valid=False, issues=issues, system1_confidence=0.8
        )

        assert 0.0 <= confidence <= 1.0
        # Invalid means high confidence in rejection (opposite of valid)
        # More issues = higher rejection confidence
        assert confidence >= 0.5

    @pytest.mark.asyncio
    async def test_verify_success(self, verifier):
        """Test successful verification"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": "VALID: YES\n\nThe code is correct."
        }
        mock_response.raise_for_status = Mock()

        verifier.client.post = AsyncMock(return_value=mock_response)

        request = VerificationRequest(
            code="def new(): return 42",
            language="python",
            context="refactor task",
            original_task="Improve function",
            system1_confidence=0.8,
        )

        result = await verifier.verify(request)

        assert isinstance(result, VerificationResponse)
        assert result.valid is True
        assert result.latency_ms >= 0  # Can be 0 on very fast operations
        assert result.model == "mistral:7b"
        assert verifier.total_verifications == 1

    @pytest.mark.asyncio
    async def test_verify_rejection(self, verifier):
        """Test verification rejection"""
        mock_response = Mock()
        mock_response.json.return_value = {
            "response": """VALID: NO

ISSUES:
- This introduces a bug

SUGGESTIONS:
- Fix the type error
"""
        }
        mock_response.raise_for_status = Mock()

        verifier.client.post = AsyncMock(return_value=mock_response)

        request = VerificationRequest(
            code="x = 'error'",
            language="python",
            context="fix task",
            original_task="Fix variable",
            system1_confidence=0.5,
        )

        result = await verifier.verify(request)

        assert result.valid is False
        assert len(result.issues) > 0
        assert verifier.rejections == 1

    @pytest.mark.asyncio
    async def test_verify_failure(self, verifier):
        """Test verification with API failure"""
        verifier.client.post = AsyncMock(
            side_effect=httpx.RequestError("Connection failed")
        )

        request = VerificationRequest(
            code="code",
            language="python",
            context="refactor task",
            original_task="Improve code",
            system1_confidence=0.7,
        )

        result = await verifier.verify(request)

        assert isinstance(result, VerificationResponse)
        assert result.valid is False
        assert "failed" in result.reasoning.lower()
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_call_ollama_http_error_retry(self, verifier):
        """Test retry logic on 5xx HTTP errors"""
        with patch("src.models.verifier.get_settings") as mock_settings:
            mock_settings.return_value.ollama_max_retries = 2
            mock_settings.return_value.ollama_retry_backoff_seconds = 0.01
            mock_settings.return_value.verifier_keep_alive = "5m"

            mock_response = Mock()
            mock_response.status_code = 503

            verifier.client.post = AsyncMock(
                side_effect=httpx.HTTPStatusError(
                    "Server error", request=Mock(), response=mock_response
                )
            )

            with pytest.raises(httpx.HTTPStatusError):
                await verifier._call_ollama("test prompt")

    def test_get_stats(self, verifier):
        """Test statistics retrieval"""
        verifier.total_verifications = 5
        verifier.total_latency = 5000.0
        verifier.rejections = 2

        stats = verifier.get_stats()

        assert stats["total_verifications"] == 5
        assert stats["avg_latency_ms"] == 1000.0
        assert stats["rejections"] == 2
        assert stats["rejection_rate"] == 0.4

    def test_get_stats_no_verifications(self, verifier):
        """Test statistics with no verifications"""
        stats = verifier.get_stats()

        assert stats["total_verifications"] == 0
        assert stats["avg_latency_ms"] == 0
        assert stats["rejection_rate"] == 0

    @pytest.mark.asyncio
    async def test_close(self, verifier):
        """Test closing HTTP client"""
        verifier.client.aclose = AsyncMock()
        await verifier.close()
        # Verifier calls aclose once
        assert verifier.client.aclose.call_count == 1


class TestReasoningRequest:
    """Test ReasoningRequest model"""

    def test_create_request(self):
        """Test creating reasoning request"""
        request = ReasoningRequest(
            task_type="refactor",
            description="Improve code",
            code_context="def foo(): pass",
            language="python",
        )

        assert request.task_type == "refactor"
        assert request.description == "Improve code"
        assert request.max_tokens == 500

    def test_request_with_selection(self):
        """Test request with selected text"""
        request = ReasoningRequest(
            task_type="fix",
            description="Fix bug",
            code_context="code",
            language="python",
            selected_text="specific code",
            max_tokens=1000,
        )

        assert request.selected_text == "specific code"
        assert request.max_tokens == 1000


class TestVerificationRequest:
    """Test VerificationRequest model"""

    def test_create_verification_request(self):
        """Test creating verification request"""
        request = VerificationRequest(
            code="new code",
            language="python",
            context="test context",
            original_task="test task",
            system1_confidence=0.8,
        )

        assert request.code == "new code"
        assert request.language == "python"
        assert request.context == "test context"
        assert request.system1_confidence == 0.8

    def test_verification_request_fields(self):
        """Test verification request with all fields"""
        request = VerificationRequest(
            code="x = 2",
            language="python",
            context="Important context",
            original_task="Fix bug",
            system1_confidence=0.85,
        )

        assert request.system1_confidence == 0.85
        assert request.context == "Important context"
        assert request.original_task == "Fix bug"
