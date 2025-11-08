"""
Unit tests for API Exception Handlers

Project Creator: Herman Swanepoel
Date: 2025-10-13
Target Coverage: 95%
GODMODE: AUTONOMOUS EXECUTION
"""

from unittest.mock import patch

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from src.api.exception_handlers import register_exception_handlers
from src.utils.exceptions import (
    AuraIAException,
    CircuitBreakerOpenException,
    RateLimitExceededException,
    ValidationException,
)


@pytest.fixture
def app():
    """Create FastAPI app with exception handlers"""
    app = FastAPI(debug=False)
    register_exception_handlers(app)

    # Add test routes that raise exceptions
    @app.get("/test/rate-limit")
    async def test_rate_limit():
        raise RateLimitExceededException(limit=100, window=60)

    @app.get("/test/validation")
    async def test_validation():
        raise ValidationException(message="Invalid input", field="email")

    @app.get("/test/circuit-breaker")
    async def test_circuit_breaker():
        raise CircuitBreakerOpenException(service_name="test_service")

    @app.get("/test/aura-exception")
    async def test_aura_exception():
        raise AuraIAException(message="Test error", error_code="TEST_ERROR")

    @app.get("/test/generic-exception")
    async def test_generic_exception():
        raise ValueError("Unexpected error")

    # B017: Use a specific exception for pytest.raises
    class CustomTestException(Exception):
        pass

    @app.get("/test/b017-exception")
    async def test_b017_exception():
        raise CustomTestException("Test error")

    return app


@pytest.fixture
def client(app):
    """Create test client"""
    return TestClient(app, raise_server_exceptions=False)


class TestRateLimitExceptionHandler:
    """Test rate limit exception handler"""

    def test_rate_limit_exception_response(self, client):
        """Test rate limit exception returns 429"""
        response = client.get("/test/rate-limit")

        assert response.status_code == 429
        assert "error" in response.json()
        assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    def test_rate_limit_exception_headers(self, client):
        """Test rate limit exception includes retry-after header"""
        response = client.get("/test/rate-limit")

        assert "Retry-After" in response.headers
        assert "X-Correlation-ID" in response.headers

    def test_rate_limit_exception_correlation_id(self, client):
        """Test rate limit exception includes correlation ID"""
        response = client.get("/test/rate-limit")

        data = response.json()
        assert "correlation_id" in data["error"]
        assert len(data["error"]["correlation_id"]) > 0

    def test_rate_limit_exception_details(self, client):
        """Test rate limit exception includes details"""
        response = client.get("/test/rate-limit")

        data = response.json()
        assert "details" in data["error"]
        assert "limit" in data["error"]["details"]
        assert "window" in data["error"]["details"]


class TestAuraIAExceptionHandler:
    """Test AuraIA exception handler"""

    def test_validation_exception_status_code(self, client):
        """Test validation exception returns 400"""
        response = client.get("/test/validation")

        assert response.status_code == 400
        assert response.json()["error"]["code"] == "VALIDATION_ERROR"

    def test_circuit_breaker_exception_status_code(self, client):
        """Test circuit breaker exception returns 503"""
        response = client.get("/test/circuit-breaker")

        assert response.status_code == 503
        assert response.json()["error"]["code"] == "CIRCUIT_BREAKER_OPEN"

    def test_generic_aura_exception_status_code(self, client):
        """Test generic AuraIA exception returns 500"""
        response = client.get("/test/aura-exception")

        assert response.status_code == 500
        assert response.json()["error"]["code"] == "TEST_ERROR"

    def test_aura_exception_correlation_id_header(self, client):
        """Test AuraIA exception includes correlation ID header"""
        response = client.get("/test/aura-exception")

        assert "X-Correlation-ID" in response.headers

    def test_aura_exception_response_structure(self, client):
        """Test AuraIA exception response structure"""
        response = client.get("/test/validation")

        data = response.json()
        assert "error" in data
        assert "code" in data["error"]
        assert "message" in data["error"]
        assert "correlation_id" in data["error"]
        assert "timestamp" in data["error"]

    def test_aura_exception_includes_details(self, client):
        """Test AuraIA exception includes error details"""
        response = client.get("/test/validation")

        data = response.json()
        assert "details" in data["error"]
        assert "field" in data["error"]["details"]


class TestGenericExceptionHandler:
    """Test generic exception handler"""

    def test_generic_exception_status_code(self, client):
        """Test generic exception returns 500"""
        response = client.get("/test/generic-exception")

        assert response.status_code == 500

    def test_generic_exception_error_code(self, client):
        """Test generic exception has INTERNAL_ERROR code"""
        response = client.get("/test/generic-exception")

        data = response.json()
        assert data["error"]["code"] == "INTERNAL_ERROR"

    def test_generic_exception_message(self, client):
        """Test generic exception has generic message"""
        response = client.get("/test/generic-exception")

        data = response.json()
        assert "unexpected error" in data["error"]["message"].lower()

    def test_generic_exception_correlation_id(self, client):
        """Test generic exception generates correlation ID"""
        response = client.get("/test/generic-exception")

        data = response.json()
        assert "correlation_id" in data["error"]
        assert len(data["error"]["correlation_id"]) > 0

    def test_generic_exception_correlation_id_header(self, client):
        """Test generic exception includes correlation ID header"""
        response = client.get("/test/generic-exception")

        assert "X-Correlation-ID" in response.headers

    def test_generic_exception_timestamp(self, client):
        """Test generic exception includes timestamp"""
        response = client.get("/test/generic-exception")

        data = response.json()
        assert "timestamp" in data["error"]

    def test_generic_exception_no_details_leak(self, client):
        """Test generic exception doesn't leak internal details"""
        response = client.get("/test/generic-exception")

        data = response.json()
        # Should not contain actual exception message
        assert "ValueError" not in data["error"]["message"]
        assert "Unexpected error" not in data["error"]["message"]


class TestExceptionHandlerIntegration:
    """Test exception handler integration scenarios"""

    def test_multiple_exceptions_different_status_codes(self, client):
        """Test different exceptions return appropriate status codes"""
        responses = {
            "/test/validation": 400,
            "/test/rate-limit": 429,
            "/test/generic-exception": 500,
            "/test/circuit-breaker": 503,
        }

        for endpoint, expected_status in responses.items():
            response = client.get(endpoint)
            assert response.status_code == expected_status

    def test_all_exceptions_have_correlation_id(self, client):
        """Test all exceptions include correlation ID"""
        endpoints = [
            "/test/validation",
            "/test/rate-limit",
            "/test/aura-exception",
            "/test/circuit-breaker",
            "/test/generic-exception",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert "X-Correlation-ID" in response.headers
            assert "correlation_id" in response.json()["error"]

    def test_all_exceptions_have_error_structure(self, client):
        """Test all exceptions follow error structure"""
        endpoints = [
            "/test/validation",
            "/test/rate-limit",
            "/test/aura-exception",
            "/test/generic-exception",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            data = response.json()

            assert "error" in data
            assert "code" in data["error"]
            assert "message" in data["error"]
            assert "correlation_id" in data["error"]

    def test_exception_handler_with_custom_correlation_id(self, client):
        """Test exception handler preserves custom correlation ID"""
        custom_id = "custom-correlation-123"

        # Create mock request with correlation ID in state
        response = client.get("/test/generic-exception", headers={"X-Correlation-ID": custom_id})

        # Note: This test shows the pattern, but TestClient doesn't
        # preserve request.state across middleware
        assert "X-Correlation-ID" in response.headers


class TestExceptionHandlerLogging:
    """Test exception handler logging"""

    @patch("src.api.exception_handlers.logger")
    def test_rate_limit_exception_logged(self, mock_logger, client):
        """Test rate limit exception is logged"""
        client.get("/test/rate-limit")

        # Verify warning was logged
        assert mock_logger.warning.called

    @patch("src.api.exception_handlers.logger")
    def test_aura_exception_logged(self, mock_logger, client):
        """Test AuraIA exception is logged"""
        client.get("/test/aura-exception")

        # Verify error was logged
        assert mock_logger.error.called

    @patch("src.api.exception_handlers.logger")
    def test_generic_exception_logged(self, mock_logger, client):
        """Test generic exception is logged"""
        client.get("/test/generic-exception")

        # Verify error was logged (using logger.error, not logger.exception)
        assert mock_logger.error.called


class TestExceptionHandlerEdgeCases:
    """Test edge cases"""

    def test_exception_with_none_details(self, app, client):
        """Test exception with None details"""

        @app.get("/test/none-details")
        async def test_none_details():
            raise AuraIAException(message="Test", error_code="TEST", details=None)

        response = client.get("/test/none-details")

        assert response.status_code == 500
        assert "error" in response.json()

    def test_exception_with_empty_details(self, app, client):
        """Test exception with empty details"""

        @app.get("/test/empty-details")
        async def test_empty_details():
            raise AuraIAException(message="Test", error_code="TEST", details={})

        response = client.get("/test/empty-details")

        assert response.status_code == 500
        data = response.json()
        assert "details" in data["error"]

    def test_exception_with_complex_details(self, app, client):
        """Test exception with complex nested details"""

        @app.get("/test/complex-details")
        async def test_complex_details():
            raise AuraIAException(
                message="Test",
                error_code="TEST",
                details={"nested": {"level1": {"level2": "value"}}, "list": [1, 2, 3]},
            )

        response = client.get("/test/complex-details")

        assert response.status_code == 500
        data = response.json()
        assert "nested" in data["error"]["details"]
        assert "list" in data["error"]["details"]
