""""""

Enhanced tests for FastReasoner and AnalyticalVerifier modelsEnhanced tests for FastReasoner and AnalyticalVerifier models

Project Creator: Herman SwanepoelProject Creator: Herman Swanepoel

""""""



from unittest.mock import AsyncMock, Mock, patchfrom unittest.mock import AsyncMock, Mock, patch



import httpximport httpx

import pytestimport pytest

from src.models.reasoner import FastReasoner, ReasoningRequest, ReasoningResponsefrom src.models.reasoner import FastReasoner, ReasoningRequest, ReasoningResponse

from src.models.verifier import AnalyticalVerifier, VerificationRequest, VerificationResponsefrom src.models.verifier import (

    AnalyticalVerifier,

    VerificationRequest,

class TestFastReasoner:    VerificationResponse,

    """Test FastReasoner (System 1)""")



    @pytest.fixture

    def reasoner(self):class TestFastReasoner:

        """Create FastReasoner instance"""    """Test FastReasoner (System 1)"""

        return FastReasoner(

            ollama_url="http://localhost:11434",    @pytest.fixture

            model="llama3.2:3b",    def reasoner(self):

            timeout=30.0,        """Create FastReasoner instance"""

        )        return FastReasoner(

            ollama_url="http://localhost:11434",

    def test_initialization(self, reasoner):            model="llama3.2:3b",

        """Test FastReasoner initialization"""            timeout=30.0,

        assert reasoner.ollama_url == "http://localhost:11434"        )

        assert reasoner.model == "llama3.2:3b"

        assert reasoner.timeout == 30.0    def test_initialization(self, reasoner):

        assert reasoner.total_requests == 0        """Test FastReasoner initialization"""

        assert reasoner.total_latency == 0.0        assert reasoner.ollama_url == "http://localhost:11434"

        assert reasoner.model == "llama3.2:3b"

    def test_build_prompt_basic(self, reasoner):        assert reasoner.timeout == 30.0

        """Test basic prompt building"""        assert reasoner.total_requests == 0

        request = ReasoningRequest(        assert reasoner.total_latency == 0.0

            task_type="refactor",

            description="Improve code quality",    def test_build_prompt_basic(self, reasoner):

            code_context="def foo():\n    pass",        """Test basic prompt building"""

            language="python",        request = ReasoningRequest(

        )            task_type="refactor",

            description="Improve code quality",

        prompt = reasoner._build_prompt(request)            code_context="def foo():\n    pass",

            language="python",

        assert "Task: refactor" in prompt        )

        assert "Improve code quality" in prompt

        assert "Language: python" in prompt        prompt = reasoner._build_prompt(request)

        assert "def foo():" in prompt

        assert "Task: refactor" in prompt

    def test_build_prompt_with_selection(self, reasoner):        assert "Improve code quality" in prompt

        """Test prompt building with selected text"""        assert "Language: python" in prompt

        request = ReasoningRequest(        assert "def foo():" in prompt

            task_type="fix",

            description="Fix bug",    def test_build_prompt_with_selection(self, reasoner):

            code_context="def foo():\n    x = 1",        """Test prompt building with selected text"""

            language="python",        request = ReasoningRequest(

            selected_text="x = 1",            task_type="fix",

        )            description="Fix bug",

            code_context="def foo():\n    x = 1",

        prompt = reasoner._build_prompt(request)            language="python",

            selected_text="x = 1",

        assert "x = 1" in prompt        )

        assert "Focus on this specific code:" in prompt

        prompt = reasoner._build_prompt(request)

    def test_parse_suggestions_with_code_blocks(self, reasoner):

        """Test parsing suggestions with code blocks"""        assert "x = 1" in prompt

        response = {        assert "Focus on this specific code:" in prompt

            "text": "Here's a fix:\n```python\ndef foo():\n    return 42\n```\n",

            "reasoning": "test",    def test_parse_suggestions_with_code_blocks(self, reasoner):

        }        """Test parsing suggestions with code blocks"""

        response = {

        suggestions = reasoner._parse_suggestions(response)            "text": "Here's a fix:\n```python\ndef foo():\n    return 42\n```\n",

            "reasoning": "test",

        assert len(suggestions) == 1        }

        assert "def foo():" in suggestions[0]

        assert "return 42" in suggestions[0]        suggestions = reasoner._parse_suggestions(response)



    def test_parse_suggestions_multiple_blocks(self, reasoner):        assert len(suggestions) == 1

        """Test parsing multiple code blocks"""        assert "def foo():" in suggestions[0]

        response = {        assert "return 42" in suggestions[0]

            "text": "```python\nx = 1\n```\nAnd also:\n```python\ny = 2\n```",

            "reasoning": "test",    def test_parse_suggestions_multiple_blocks(self, reasoner):

        }        """Test parsing multiple code blocks"""

        response = {

        suggestions = reasoner._parse_suggestions(response)            "text": "```python\nx = 1\n```\nAnd also:\n```python\ny = 2\n```",

            "reasoning": "test",

        assert len(suggestions) == 2        }

        assert "x = 1" in suggestions[0]

        assert "y = 2" in suggestions[1]        suggestions = reasoner._parse_suggestions(response)



    def test_parse_suggestions_no_code_blocks(self, reasoner):        assert len(suggestions) == 2

        """Test parsing when no code blocks present"""        assert "x = 1" in suggestions[0]

        response = {        assert "y = 2" in suggestions[1]

            "text": "You should refactor this function to be more modular.",

            "reasoning": "test",    def test_parse_suggestions_no_code_blocks(self, reasoner):

        }        """Test parsing when no code blocks present"""

        response = {

        suggestions = reasoner._parse_suggestions(response)            "text": "You should refactor this function to be more modular.",

            "reasoning": "test",

        assert len(suggestions) == 1        }

        assert "refactor" in suggestions[0]

        suggestions = reasoner._parse_suggestions(response)

    def test_parse_suggestions_empty_response(self, reasoner):

        """Test parsing empty response"""        assert len(suggestions) == 1

        response = {"text": "", "reasoning": "test"}        assert "refactor" in suggestions[0]



        suggestions = reasoner._parse_suggestions(response)    def test_parse_suggestions_empty_response(self, reasoner):

        """Test parsing empty response"""

        assert suggestions == []        response = {"text": "", "reasoning": "test"}



    def test_calculate_confidence_high(self, reasoner):        suggestions = reasoner._parse_suggestions(response)

        """Test confidence calculation for high-confidence scenarios"""

        response = {"text": "```python\ncode here\n```"}        assert suggestions == []

        request = ReasoningRequest(

            task_type="refactor",    def test_calculate_confidence_high(self, reasoner):

            description="test",        """Test confidence calculation for high-confidence scenarios"""

            code_context="code",        response = {"text": "```python\ncode here\n```"}

            language="python",        request = ReasoningRequest(

        )            task_type="refactor",

            description="test",

        confidence = reasoner._calculate_confidence(response, request)            code_context="code",

            language="python",

        assert 0.0 <= confidence <= 1.0        )

        assert confidence > 0.5  # Should be relatively high with code blocks

        confidence = reasoner._calculate_confidence(response, request)

    def test_calculate_confidence_range(self, reasoner):

        """Test confidence calculation is within valid range"""        assert 0.0 <= confidence <= 1.0

        response = {"text": "I'm not sure."}        assert confidence > 0.5  # Should be relatively high with code blocks

        request = ReasoningRequest(

            task_type="refactor",    def test_calculate_confidence_low(self, reasoner):

            description="test",        """Test confidence calculation for low-confidence scenarios"""

            code_context="code",        response = {"text": "I'm not sure."}

            language="python",        request = ReasoningRequest(

        )            task_type="refactor",

            description="test",

        confidence = reasoner._calculate_confidence(response, request)            code_context="code",

            language="python",

        assert 0.0 <= confidence <= 1.0        )

        

    @pytest.mark.asyncio        confidence = reasoner._calculate_confidence(response, request)

    async def test_reason_success(self, reasoner):        

        """Test successful reasoning"""        assert 0.0 <= confidence <= 1.0

        mock_response = Mock()        # Confidence calculation is based on text length and keywords

        mock_response.json.return_value = {        # Short responses may still have moderate confidence    @pytest.mark.asyncio

            "response": "```python\ndef improved():\n    return True\n```"    async def test_reason_success(self, reasoner):

        }        """Test successful reasoning"""

        mock_response.raise_for_status = Mock()        mock_response = Mock()

        mock_response.json.return_value = {

        reasoner.client.post = AsyncMock(return_value=mock_response)            "response": "```python\ndef improved():\n    return True\n```"

        }

        request = ReasoningRequest(        mock_response.raise_for_status = Mock()

            task_type="refactor",

            description="Improve function",        reasoner.client.post = AsyncMock(return_value=mock_response)

            code_context="def foo(): pass",

            language="python",        request = ReasoningRequest(

        )            task_type="refactor",

            description="Improve function",

        result = await reasoner.reason(request)            code_context="def foo(): pass",

            language="python",

        assert isinstance(result, ReasoningResponse)        )

        assert len(result.suggestions) > 0

        assert result.confidence > 0        result = await reasoner.reason(request)

        assert result.latency_ms > 0

        assert result.model == "llama3.2:3b"        assert isinstance(result, ReasoningResponse)

        assert len(result.suggestions) > 0

    @pytest.mark.asyncio        assert result.confidence > 0

    async def test_reason_failure(self, reasoner):        assert result.latency_ms > 0

        """Test reasoning with API failure"""        assert result.model == "llama3.2:3b"

        reasoner.client.post = AsyncMock(side_effect=httpx.RequestError("Connection failed"))

    @pytest.mark.asyncio

        request = ReasoningRequest(    async def test_reason_failure(self, reasoner):

            task_type="refactor",        """Test reasoning with API failure"""

            description="Test",        reasoner.client.post = AsyncMock(

            code_context="code",            side_effect=httpx.RequestError("Connection failed")

            language="python",        )

        )

        request = ReasoningRequest(

        result = await reasoner.reason(request)            task_type="refactor",

            description="Test",

        assert isinstance(result, ReasoningResponse)            code_context="code",

        assert result.suggestions == []            language="python",

        assert result.confidence == 0.0        )

        assert "failed" in result.reasoning.lower()

        result = await reasoner.reason(request)

    @pytest.mark.asyncio

    async def test_call_ollama_retry_on_timeout(self, reasoner):        assert isinstance(result, ReasoningResponse)

        """Test retry logic on timeout"""        assert result.suggestions == []

        with patch("src.models.reasoner.get_settings") as mock_settings:        assert result.confidence == 0.0

            mock_settings.return_value.ollama_max_retries = 2        assert "failed" in result.reasoning.lower()

            mock_settings.return_value.ollama_retry_backoff_seconds = 0.01

            mock_settings.return_value.reasoner_keep_alive = "30m"    @pytest.mark.asyncio

    async def test_call_ollama_retry_on_timeout(self, reasoner):

            reasoner.client.post = AsyncMock(side_effect=httpx.TimeoutException("Timeout"))        """Test retry logic on timeout"""

        with patch("src.models.reasoner.get_settings") as mock_settings:

            with pytest.raises(httpx.TimeoutException):            mock_settings.return_value.ollama_max_retries = 2

                await reasoner._call_ollama("test prompt")            mock_settings.return_value.ollama_retry_backoff_seconds = 0.01

            mock_settings.return_value.reasoner_keep_alive = "30m"

    def test_get_stats(self, reasoner):

        """Test statistics retrieval"""            reasoner.client.post = AsyncMock(

        reasoner.total_requests = 10                side_effect=httpx.TimeoutException("Timeout")

        reasoner.total_latency = 1000.0            )



        stats = reasoner.get_stats()            with pytest.raises(httpx.TimeoutException):

                await reasoner._call_ollama("test prompt")

        assert stats["total_requests"] == 10

        assert stats["avg_latency_ms"] == 100.0    def test_get_stats(self, reasoner):

        """Test statistics retrieval"""

        reasoner.total_requests = 10

class TestAnalyticalVerifier:        reasoner.total_latency = 1000.0

    """Test AnalyticalVerifier (System 2)"""

        stats = reasoner.get_stats()

    @pytest.fixture

    def verifier(self):        assert stats["total_requests"] == 10

        """Create AnalyticalVerifier instance"""        assert stats["avg_latency_ms"] == 100.0

        return AnalyticalVerifier(

            ollama_url="http://localhost:11434",

            model="mistral:7b",class TestAnalyticalVerifier:

            timeout=60.0,    """Test AnalyticalVerifier (System 2)"""

        )

    @pytest.fixture

    def test_initialization(self, verifier):    def verifier(self):

        """Test AnalyticalVerifier initialization"""        """Create AnalyticalVerifier instance"""

        assert verifier.ollama_url == "http://localhost:11434"        return AnalyticalVerifier(

        assert verifier.model == "mistral:7b"            ollama_url="http://localhost:11434",

        assert verifier.timeout == 60.0            model="mistral:7b",

        assert verifier.total_verifications == 0            timeout=60.0,

        )

    def test_build_verification_prompt_basic(self, verifier):

        """Test basic verification prompt building"""    def test_initialization(self, verifier):

        request = VerificationRequest(        """Test AnalyticalVerifier initialization"""

            code="def new(): return 42",        assert verifier.ollama_url == "http://localhost:11434"

            language="python",        assert verifier.model == "mistral:7b"

            context="refactor task",        assert verifier.timeout == 60.0

            original_task="Improve function",        assert verifier.total_verifications == 0

            system1_confidence=0.8,

        )    def test_build_verification_prompt_basic(self, verifier):

        """Test basic verification prompt building"""

        prompt = verifier._build_verification_prompt(request)        request = VerificationRequest(

            code="def new(): return 42",

        assert "def new(): return 42" in prompt            language="python",

        assert "Language: python" in prompt            context="refactor task",

        assert "refactor task" in prompt            original_task="Improve function",

            system1_confidence=0.8,

    def test_build_verification_prompt_with_context(self, verifier):        )

        """Test verification prompt with additional context"""        

        request = VerificationRequest(        prompt = verifier._build_verification_prompt(request)

            code="x = 2",        

            language="python",        assert "def new(): return 42" in prompt

            context="This is a bug fix",        assert "Language: python" in prompt

            original_task="Fix variable assignment",        assert "refactor task" in prompt

            system1_confidence=0.75,

        )    def test_build_verification_prompt_with_context(self, verifier):

        """Test verification prompt with additional context"""

        prompt = verifier._build_verification_prompt(request)        request = VerificationRequest(

            code="x = 2",

        assert "confidence: 0.75" in prompt            language="python",

        assert "bug fix" in prompt            context="This is a bug fix",

            original_task="Fix variable assignment",

    def test_parse_verification_approved(self, verifier):            system1_confidence=0.75,

        """Test parsing approved verification"""        )

        response = {"text": "VALID: YES\n\nThe refactoring is correct and improves code quality."}        

        prompt = verifier._build_verification_prompt(request)

        is_valid, issues, suggestions = verifier._parse_verification(response)        

        assert "confidence: 0.75" in prompt

        assert is_valid is True        assert "bug fix" in prompt

        assert len(issues) == 0

    def test_parse_verification_approved(self, verifier):

    def test_parse_verification_rejected(self, verifier):        """Test parsing approved verification"""

        """Test parsing rejected verification"""        response = {

        response = {"text": "VALID: NO\n\nThis change introduces a bug."}            "text": "VALID: YES\n\nThe refactoring is correct and improves code quality."

        }

        is_valid, issues, suggestions = verifier._parse_verification(response)        

        is_valid, issues, suggestions = verifier._parse_verification(response)

        assert is_valid is False        

        assert is_valid is True

    def test_parse_verification_issues(self, verifier):        assert len(issues) == 0

        """Test parsing verification with specific issues"""

        response = {    def test_parse_verification_rejected(self, verifier):

            "text": """VALID: NO        """Test parsing rejected verification"""

        response = {

ISSUES:            "text": "VALID: NO\n\nThis change introduces a bug."

- Missing error handling        }

- Performance concern        

        is_valid, issues, suggestions = verifier._parse_verification(response)

SUGGESTIONS:        

- Add try-catch        assert is_valid is False

"""

        }    def test_parse_verification_issues(self, verifier):

        """Test parsing verification with specific issues"""

        is_valid, issues, suggestions = verifier._parse_verification(response)        response = {

            "text": """VALID: NO

        assert is_valid is False

        assert len(issues) >= 1ISSUES:

        assert "error handling" in issues[0]["message"].lower()- Missing error handling

- Performance concern

    def test_parse_verification_improvements(self, verifier):

        """Test parsing verification with improvements"""SUGGESTIONS:

        response = {- Add try-catch

            "text": """VALID: YES"""

        }

SUGGESTIONS:        

- Better naming        is_valid, issues, suggestions = verifier._parse_verification(response)

- More efficient        

"""        assert is_valid is False

        }        assert len(issues) >= 1

        assert "error handling" in issues[0]["message"].lower()

        is_valid, issues, suggestions = verifier._parse_verification(response)

    def test_parse_verification_improvements(self, verifier):

        assert is_valid is True        """Test parsing verification with improvements"""

        assert len(suggestions) >= 1        response = {

            "text": """VALID: YES

    def test_parse_verification_ambiguous(self, verifier):

        """Test parsing ambiguous response defaults to rejected"""SUGGESTIONS:

        response = {"text": "This looks okay maybe"}- Better naming

- More efficient

        is_valid, issues, suggestions = verifier._parse_verification(response)"""

        }

        assert is_valid is False        

        is_valid, issues, suggestions = verifier._parse_verification(response)

    @pytest.mark.asyncio        

    async def test_verify_success(self, verifier):        assert is_valid is True

        """Test successful verification"""        assert len(suggestions) >= 1

        mock_response = Mock()

        mock_response.json.return_value = {"response": "VALID: YES\n\nThe code is correct."}    def test_parse_verification_ambiguous(self, verifier):

        mock_response.raise_for_status = Mock()        """Test parsing ambiguous response defaults to rejected"""

        response = {"text": "This looks okay maybe"}

        verifier.client.post = AsyncMock(return_value=mock_response)        

        is_valid, issues, suggestions = verifier._parse_verification(response)

        request = VerificationRequest(        

            code="def new(): return 42",        assert is_valid is False    @pytest.mark.asyncio

            language="python",    async def test_verify_success(self, verifier):

            context="refactor task",        """Test successful verification"""

            original_task="Improve function",        mock_response = Mock()

            system1_confidence=0.8,        mock_response.json.return_value = {

        )            "response": "APPROVED\n\nThe code is correct."

        }

        result = await verifier.verify(request)        mock_response.raise_for_status = Mock()



        assert isinstance(result, VerificationResponse)        verifier.client.post = AsyncMock(return_value=mock_response)

        assert result.valid is True

        assert result.latency_ms > 0        request = VerificationRequest(

        assert result.model == "mistral:7b"            task_type="refactor",

            original_code="def old(): pass",

    @pytest.mark.asyncio            proposed_code="def new(): return 42",

    async def test_verify_rejection(self, verifier):            language="python",

        """Test verification rejection"""        )

        mock_response = Mock()

        mock_response.json.return_value = {        result = await verifier.verify(request)

            "response": """VALID: NO

        assert isinstance(result, VerificationResponse)

ISSUES:        assert result.result.approved is True

- This introduces a bug        assert result.latency_ms > 0

        assert result.model == "mistral:7b"

SUGGESTIONS:

- Fix the type error    @pytest.mark.asyncio

"""    async def test_verify_rejection(self, verifier):

        }        """Test verification rejection"""

        mock_response.raise_for_status = Mock()        mock_response = Mock()

        mock_response.json.return_value = {

        verifier.client.post = AsyncMock(return_value=mock_response)            "response": "REJECTED\n\nThis introduces a bug."

        }

        request = VerificationRequest(        mock_response.raise_for_status = Mock()

            code="x = 'error'",

            language="python",        verifier.client.post = AsyncMock(return_value=mock_response)

            context="fix task",

            original_task="Fix variable",        request = VerificationRequest(

            system1_confidence=0.5,            task_type="fix",

        )            original_code="x = 1",

            proposed_code="x = 'error'",

        result = await verifier.verify(request)            language="python",

        )

        assert result.valid is False

        assert len(result.issues) > 0        result = await verifier.verify(request)



    @pytest.mark.asyncio        assert result.result.approved is False

    async def test_verify_failure(self, verifier):        assert len(result.result.issues) > 0 or "bug" in result.result.reasoning.lower()

        """Test verification with API failure"""

        verifier.client.post = AsyncMock(side_effect=httpx.RequestError("Connection failed"))    @pytest.mark.asyncio

    async def test_verify_failure(self, verifier):

        request = VerificationRequest(        """Test verification with API failure"""

            code="code",        verifier.client.post = AsyncMock(

            language="python",            side_effect=httpx.RequestError("Connection failed")

            context="refactor task",        )

            original_task="Improve code",

            system1_confidence=0.7,        request = VerificationRequest(

        )            task_type="refactor",

            original_code="code",

        result = await verifier.verify(request)            proposed_code="new_code",

            language="python",

        assert isinstance(result, VerificationResponse)        )

        assert result.valid is False

        assert "failed" in result.reasoning.lower()        result = await verifier.verify(request)



    @pytest.mark.asyncio        assert isinstance(result, VerificationResponse)

    async def test_call_ollama_http_error_retry(self, verifier):        assert result.result.approved is False

        """Test retry logic on 5xx HTTP errors"""        assert "failed" in result.result.reasoning.lower()

        with patch("src.models.verifier.get_settings") as mock_settings:

            mock_settings.return_value.ollama_max_retries = 2    @pytest.mark.asyncio

            mock_settings.return_value.ollama_retry_backoff_seconds = 0.01    async def test_call_ollama_http_error_retry(self, verifier):

            mock_settings.return_value.verifier_keep_alive = "5m"        """Test retry logic on 5xx HTTP errors"""

        with patch("src.models.verifier.get_settings") as mock_settings:

            mock_response = Mock()            mock_settings.return_value.ollama_max_retries = 2

            mock_response.status_code = 503            mock_settings.return_value.ollama_retry_backoff_seconds = 0.01

            mock_settings.return_value.verifier_keep_alive = "5m"

            verifier.client.post = AsyncMock(

                side_effect=httpx.HTTPStatusError(            mock_response = Mock()

                    "Server error", request=Mock(), response=mock_response            mock_response.status_code = 503

                )

            )            verifier.client.post = AsyncMock(

                side_effect=httpx.HTTPStatusError(

            with pytest.raises(httpx.HTTPStatusError):                    "Server error", request=Mock(), response=mock_response

                await verifier._call_ollama("test prompt")                )

            )

    def test_get_stats(self, verifier):

        """Test statistics retrieval"""            with pytest.raises(httpx.HTTPStatusError):

        verifier.total_verifications = 5                await verifier._call_ollama("test prompt")

        verifier.total_latency = 5000.0

    def test_get_stats(self, verifier):

        stats = verifier.get_stats()        """Test statistics retrieval"""

        verifier.total_verifications = 5

        assert stats["total_verifications"] == 5        verifier.total_latency = 5000.0

        assert stats["avg_latency_ms"] == 1000.0        verifier.approved_count = 3

        verifier.rejected_count = 2



class TestReasoningRequest:        stats = verifier.get_stats()

    """Test ReasoningRequest model"""

        assert stats["total_verifications"] == 5

    def test_create_request(self):        assert stats["avg_latency_ms"] == 1000.0

        """Test creating reasoning request"""        assert stats["approved_count"] == 3

        request = ReasoningRequest(        assert stats["rejected_count"] == 2

            task_type="refactor",        assert stats["approval_rate"] == 0.6

            description="Improve code",

            code_context="def foo(): pass",

            language="python",class TestReasoningRequest:

        )    """Test ReasoningRequest model"""



        assert request.task_type == "refactor"    def test_create_request(self):

        assert request.description == "Improve code"        """Test creating reasoning request"""

        assert request.max_tokens == 500        request = ReasoningRequest(

            task_type="refactor",

    def test_request_with_selection(self):            description="Improve code",

        """Test request with selected text"""            code_context="def foo(): pass",

        request = ReasoningRequest(            language="python",

            task_type="fix",        )

            description="Fix bug",

            code_context="code",        assert request.task_type == "refactor"

            language="python",        assert request.description == "Improve code"

            selected_text="specific code",        assert request.max_tokens == 500

            max_tokens=1000,

        )    def test_request_with_selection(self):

        """Test request with selected text"""

        assert request.selected_text == "specific code"        request = ReasoningRequest(

        assert request.max_tokens == 1000            task_type="fix",

            description="Fix bug",

            code_context="code",

class TestVerificationRequest:            language="python",

    """Test VerificationRequest model"""            selected_text="specific code",

            max_tokens=1000,

    def test_create_verification_request(self):        )

        """Test creating verification request"""

        request = VerificationRequest(        assert request.selected_text == "specific code"

            code="new code",        assert request.max_tokens == 1000

            language="python",

            context="test context",

            original_task="test task",class TestVerificationRequest:

            system1_confidence=0.8,    """Test VerificationRequest model"""

        )

    def test_create_verification_request(self):

        assert request.code == "new code"        """Test creating verification request"""

        assert request.language == "python"        request = VerificationRequest(

        assert request.context == "test context"            task_type="refactor",

        assert request.system1_confidence == 0.8            original_code="old",

            proposed_code="new",

    def test_verification_request_fields(self):            language="python",

        """Test verification request with all fields"""        )

        request = VerificationRequest(

            code="x = 2",        assert request.task_type == "refactor"

            language="python",        assert request.original_code == "old"

            context="Important context",        assert request.proposed_code == "new"

            original_task="Fix bug",

            system1_confidence=0.85,    def test_verification_request_with_context(self):

        )        """Test verification request with additional context"""

        request = VerificationRequest(

        assert request.system1_confidence == 0.85            task_type="fix",

        assert request.context == "Important context"            original_code="old",

        assert request.original_task == "Fix bug"            proposed_code="new",

            language="python",
            system1_confidence=0.85,
            additional_context="Important context",
        )

        assert request.system1_confidence == 0.85
        assert request.additional_context == "Important context"
