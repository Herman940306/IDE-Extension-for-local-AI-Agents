"""
Unit tests for exception hierarchy

Project Creator: Herman Swanepoel
Date: 2025-10-13
Target Coverage: 100%
"""

import pytest
from datetime import datetime
from src.utils.exceptions import (
    AuraIAException,
    AdapterException,
    LLMException,
    ValidationException,
    CircuitBreakerOpenException,
    RateLimitExceededException,
)


class TestAuraIAException:
    """Test base AuraIA exception"""

    def test_initialization_with_required_params(self):
        """Test exception initialization with required parameters"""
        exc = AuraIAException(message="Test error", error_code="TEST_ERROR")

        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.details == {}
        assert exc.correlation_id is not None
        assert exc.timestamp is not None

    def test_initialization_with_all_params(self):
        """Test exception initialization with all parameters"""
        details = {"key": "value"}
        correlation_id = "test-correlation-123"

        exc = AuraIAException(
            message="Test error",
            error_code="TEST_ERROR",
            details=details,
            correlation_id=correlation_id,
        )

        assert exc.message == "Test error"
        assert exc.error_code == "TEST_ERROR"
        assert exc.details == details
        assert exc.correlation_id == correlation_id

    def test_auto_generated_correlation_id(self):
        """Test that correlation ID is auto-generated if not provided"""
        exc1 = AuraIAException(message="Test 1", error_code="TEST_1")
        exc2 = AuraIAException(message="Test 2", error_code="TEST_2")

        assert exc1.correlation_id != exc2.correlation_id
        assert len(exc1.correlation_id) > 0

    def test_timestamp_generation(self):
        """Test that timestamp is generated on creation"""
        exc = AuraIAException(message="Test", error_code="TEST")

        # Parse timestamp to verify it's valid ISO format
        timestamp = datetime.fromisoformat(exc.timestamp)
        assert isinstance(timestamp, datetime)

    def test_to_dict(self):
        """Test conversion to dictionary"""
        exc = AuraIAException(
            message="Test error",
            error_code="TEST_ERROR",
            details={"key": "value"},
            correlation_id="test-123",
        )

        result = exc.to_dict()

        assert "error" in result
        assert result["error"]["code"] == "TEST_ERROR"
        assert result["error"]["message"] == "Test error"
        assert result["error"]["details"] == {"key": "value"}
        assert result["error"]["correlation_id"] == "test-123"
        assert "timestamp" in result["error"]

    def test_str_representation(self):
        """Test string representation"""
        exc = AuraIAException(
            message="Test error", error_code="TEST_ERROR", correlation_id="test-123"
        )

        str_repr = str(exc)

        assert "TEST_ERROR" in str_repr
        assert "Test error" in str_repr
        assert "test-123" in str_repr

    def test_exception_can_be_raised(self):
        """Test that exception can be raised and caught"""
        with pytest.raises(AuraIAException) as exc_info:
            raise AuraIAException(message="Test", error_code="TEST")

        assert exc_info.value.message == "Test"
        assert exc_info.value.error_code == "TEST"


class TestAdapterException:
    """Test adapter-specific exception"""

    def test_initialization(self):
        """Test adapter exception initialization"""
        exc = AdapterException(message="Adapter failed", adapter_name="test_adapter")

        assert exc.message == "Adapter failed"
        assert exc.error_code == "ADAPTER_ERROR"
        assert exc.details["adapter"] == "test_adapter"

    def test_with_additional_details(self):
        """Test adapter exception with additional details"""
        exc = AdapterException(
            message="Adapter failed",
            adapter_name="test_adapter",
            details={"reason": "timeout", "duration": 30},
        )

        assert exc.details["adapter"] == "test_adapter"
        assert exc.details["reason"] == "timeout"
        assert exc.details["duration"] == 30

    def test_with_correlation_id(self):
        """Test adapter exception with correlation ID"""
        exc = AdapterException(
            message="Adapter failed", adapter_name="test_adapter", correlation_id="adapter-123"
        )

        assert exc.correlation_id == "adapter-123"

    def test_inherits_from_base(self):
        """Test that AdapterException inherits from AuraIAException"""
        exc = AdapterException(message="Test", adapter_name="test")
        assert isinstance(exc, AuraIAException)


class TestLLMException:
    """Test LLM-specific exception"""

    def test_initialization(self):
        """Test LLM exception initialization"""
        exc = LLMException(message="LLM inference failed", model="codellama:7b")

        assert exc.message == "LLM inference failed"
        assert exc.error_code == "LLM_ERROR"
        assert exc.details["model"] == "codellama:7b"

    def test_with_additional_details(self):
        """Test LLM exception with additional details"""
        exc = LLMException(
            message="LLM inference failed",
            model="codellama:7b",
            details={"reason": "timeout", "tokens": 1000},
        )

        assert exc.details["model"] == "codellama:7b"
        assert exc.details["reason"] == "timeout"
        assert exc.details["tokens"] == 1000

    def test_inherits_from_base(self):
        """Test that LLMException inherits from AuraIAException"""
        exc = LLMException(message="Test", model="test-model")
        assert isinstance(exc, AuraIAException)


class TestValidationException:
    """Test validation exception"""

    def test_initialization(self):
        """Test validation exception initialization"""
        exc = ValidationException(message="Invalid input", field="email")

        assert exc.message == "Invalid input"
        assert exc.error_code == "VALIDATION_ERROR"
        assert exc.details["field"] == "email"

    def test_with_additional_details(self):
        """Test validation exception with additional details"""
        exc = ValidationException(
            message="Invalid input",
            field="email",
            details={"value": "invalid@", "constraint": "email_format"},
        )

        assert exc.details["field"] == "email"
        assert exc.details["value"] == "invalid@"
        assert exc.details["constraint"] == "email_format"

    def test_inherits_from_base(self):
        """Test that ValidationException inherits from AuraIAException"""
        exc = ValidationException(message="Test", field="test_field")
        assert isinstance(exc, AuraIAException)


class TestCircuitBreakerOpenException:
    """Test circuit breaker exception"""

    def test_initialization(self):
        """Test circuit breaker exception initialization"""
        exc = CircuitBreakerOpenException(service_name="test_service")

        assert "test_service" in exc.message
        assert exc.error_code == "CIRCUIT_BREAKER_OPEN"
        assert exc.details["service"] == "test_service"

    def test_with_additional_details(self):
        """Test circuit breaker exception with additional details"""
        exc = CircuitBreakerOpenException(
            service_name="test_service",
            details={"failure_count": 5, "last_failure": "2025-10-13T10:00:00Z"},
        )

        assert exc.details["service"] == "test_service"
        assert exc.details["failure_count"] == 5
        assert exc.details["last_failure"] == "2025-10-13T10:00:00Z"

    def test_inherits_from_base(self):
        """Test that CircuitBreakerOpenException inherits from AuraIAException"""
        exc = CircuitBreakerOpenException(service_name="test")
        assert isinstance(exc, AuraIAException)


class TestRateLimitExceededException:
    """Test rate limit exception"""

    def test_initialization(self):
        """Test rate limit exception initialization"""
        exc = RateLimitExceededException(limit=100, window=60)

        assert "100" in exc.message
        assert "60" in exc.message
        assert exc.error_code == "RATE_LIMIT_EXCEEDED"
        assert exc.details["limit"] == 100
        assert exc.details["window"] == 60

    def test_with_additional_details(self):
        """Test rate limit exception with additional details"""
        exc = RateLimitExceededException(
            limit=100, window=60, details={"client_id": "client-123", "current_count": 105}
        )

        assert exc.details["limit"] == 100
        assert exc.details["window"] == 60
        assert exc.details["client_id"] == "client-123"
        assert exc.details["current_count"] == 105

    def test_inherits_from_base(self):
        """Test that RateLimitExceededException inherits from AuraIAException"""
        exc = RateLimitExceededException(limit=100, window=60)
        assert isinstance(exc, AuraIAException)


class TestExceptionHierarchy:
    """Test exception hierarchy relationships"""

    def test_all_exceptions_inherit_from_base(self):
        """Test that all custom exceptions inherit from AuraIAException"""
        exceptions = [
            AdapterException(message="Test", adapter_name="test"),
            LLMException(message="Test", model="test"),
            ValidationException(message="Test", field="test"),
            CircuitBreakerOpenException(service_name="test"),
            RateLimitExceededException(limit=100, window=60),
        ]

        for exc in exceptions:
            assert isinstance(exc, AuraIAException)
            assert isinstance(exc, Exception)

    def test_all_exceptions_have_to_dict(self):
        """Test that all exceptions can be converted to dict"""
        exceptions = [
            AuraIAException(message="Test", error_code="TEST"),
            AdapterException(message="Test", adapter_name="test"),
            LLMException(message="Test", model="test"),
            ValidationException(message="Test", field="test"),
            CircuitBreakerOpenException(service_name="test"),
            RateLimitExceededException(limit=100, window=60),
        ]

        for exc in exceptions:
            result = exc.to_dict()
            assert "error" in result
            assert "code" in result["error"]
            assert "message" in result["error"]
            assert "correlation_id" in result["error"]
            assert "timestamp" in result["error"]

    def test_all_exceptions_have_str_representation(self):
        """Test that all exceptions have string representation"""
        exceptions = [
            AuraIAException(message="Test", error_code="TEST"),
            AdapterException(message="Test", adapter_name="test"),
            LLMException(message="Test", model="test"),
            ValidationException(message="Test", field="test"),
            CircuitBreakerOpenException(service_name="test"),
            RateLimitExceededException(limit=100, window=60),
        ]

        for exc in exceptions:
            str_repr = str(exc)
            assert len(str_repr) > 0
            assert exc.error_code in str_repr
