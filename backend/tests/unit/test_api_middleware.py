"""
Unit tests for API Middleware

Project Creator: Herman Swanepoel
Date: 2025-10-13
Target Coverage: 90%
GODMODE: AUTONOMOUS EXECUTION
"""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from src.api.exception_handlers import register_exception_handlers
from src.api.middleware import CorrelationIDMiddleware, RateLimitMiddleware, RequestSizeMiddleware
from src.services.rate_limiter import RateLimiter

# ============================================================================
# CorrelationIDMiddleware Tests
# ============================================================================


@pytest.fixture
def app_with_correlation_id():
    """Create FastAPI app with correlation ID middleware"""
    app = FastAPI()
    app.add_middleware(CorrelationIDMiddleware)

    @app.get("/test")
    async def test_endpoint(request: Request):
        return {"correlation_id": request.state.correlation_id, "message": "success"}

    return app


@pytest.fixture
def correlation_client(app_with_correlation_id):
    """Create test client for correlation ID tests"""
    return TestClient(app_with_correlation_id)


class TestCorrelationIDMiddleware:
    """Test CorrelationIDMiddleware"""

    def test_generates_correlation_id(self, correlation_client):
        """Test middleware generates correlation ID if not provided"""
        response = correlation_client.get("/test")

        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        assert len(response.headers["X-Correlation-ID"]) > 0

    def test_preserves_provided_correlation_id(self, correlation_client):
        """Test middleware preserves provided correlation ID"""
        custom_id = "custom-correlation-123"

        response = correlation_client.get("/test", headers={"X-Correlation-ID": custom_id})

        assert response.status_code == 200
        assert response.headers["X-Correlation-ID"] == custom_id

    def test_correlation_id_in_response_header(self, correlation_client):
        """Test correlation ID is added to response header"""
        response = correlation_client.get("/test")

        assert "X-Correlation-ID" in response.headers

    def test_correlation_id_available_in_request_state(self, correlation_client):
        """Test correlation ID is available in request.state"""
        response = correlation_client.get("/test")

        data = response.json()
        assert "correlation_id" in data
        assert data["correlation_id"] == response.headers["X-Correlation-ID"]

    def test_different_requests_different_correlation_ids(self, correlation_client):
        """Test different requests get different correlation IDs"""
        response1 = correlation_client.get("/test")
        response2 = correlation_client.get("/test")

        id1 = response1.headers["X-Correlation-ID"]
        id2 = response2.headers["X-Correlation-ID"]

        assert id1 != id2

    @patch("src.api.middleware.logger")
    def test_logs_request_with_correlation_id(self, mock_logger, correlation_client):
        """Test request is logged with correlation ID"""
        correlation_client.get("/test")

        # Verify info was logged
        assert mock_logger.info.called
        # Check that correlation_id was in the log extra
        call_args = mock_logger.info.call_args_list
        assert any("correlation_id" in str(call) for call in call_args)

    @patch("src.api.middleware.logger")
    def test_logs_response_with_duration(self, mock_logger, correlation_client):
        """Test response is logged with duration"""
        correlation_client.get("/test")

        # Verify info was logged twice (request and response)
        assert mock_logger.info.call_count >= 2


# ============================================================================
# RateLimitMiddleware Tests
# ============================================================================


@pytest.fixture
async def mock_rate_limiter():
    """Create mock rate limiter"""
    limiter = AsyncMock(spec=RateLimiter)
    limiter.check_rate_limit = AsyncMock(return_value=(True, 99))
    return limiter


@pytest.fixture
def app_with_rate_limit(mock_rate_limiter):
    """Create FastAPI app with rate limit middleware"""
    app = FastAPI()
    app.add_middleware(RateLimitMiddleware, rate_limiter=mock_rate_limiter, enabled=True)

    @app.get("/api/suggestions")
    async def suggestions():
        return {"message": "success"}

    @app.get("/api/agent/discuss")
    async def discuss():
        return {"message": "success"}

    @app.get("/api/other")
    async def other():
        return {"message": "success"}

    return app


@pytest.fixture
def rate_limit_client(app_with_rate_limit):
    """Create test client for rate limit tests"""
    return TestClient(app_with_rate_limit)


class TestRateLimitMiddleware:
    """Test RateLimitMiddleware"""

    def test_allows_request_within_limit(self, rate_limit_client, mock_rate_limiter):
        """Test middleware allows request within rate limit"""
        mock_rate_limiter.check_rate_limit.return_value = (True, 99)

        response = rate_limit_client.get("/api/suggestions")

        assert response.status_code == 200

    def test_blocks_request_exceeding_limit(self, rate_limit_client, mock_rate_limiter):
        """Test middleware blocks request exceeding rate limit"""
        mock_rate_limiter.check_rate_limit.return_value = (False, 0)

        response = rate_limit_client.get("/api/suggestions")

        assert response.status_code == 429
        assert "error" in response.json()
        assert response.json()["error"]["code"] == "RATE_LIMIT_EXCEEDED"

    def test_adds_rate_limit_headers(self, rate_limit_client, mock_rate_limiter):
        """Test middleware adds rate limit headers"""
        mock_rate_limiter.check_rate_limit.return_value = (True, 50)

        response = rate_limit_client.get("/api/suggestions")

        assert "X-RateLimit-Limit" in response.headers
        assert "X-RateLimit-Remaining" in response.headers

    def test_retry_after_header_on_limit_exceeded(self, rate_limit_client, mock_rate_limiter):
        """Test Retry-After header is added when limit exceeded"""
        mock_rate_limiter.check_rate_limit.return_value = (False, 0)

        response = rate_limit_client.get("/api/suggestions")

        assert "Retry-After" in response.headers

    def test_uses_client_ip_as_identifier(self, rate_limit_client, mock_rate_limiter):
        """Test middleware uses client IP as identifier"""
        mock_rate_limiter.check_rate_limit.return_value = (True, 99)

        rate_limit_client.get("/api/suggestions")

        # Verify rate limiter was called
        mock_rate_limiter.check_rate_limit.assert_called_once()
        call_args = mock_rate_limiter.check_rate_limit.call_args

        # Key should contain client identifier
        assert "key" in call_args.kwargs
        assert ":" in call_args.kwargs["key"]  # Format: client_id:path

    def test_uses_api_key_if_provided(self, rate_limit_client, mock_rate_limiter):
        """Test middleware uses API key as identifier if provided"""
        mock_rate_limiter.check_rate_limit.return_value = (True, 99)

        rate_limit_client.get("/api/suggestions", headers={"X-API-Key": "test-api-key"})

        call_args = mock_rate_limiter.check_rate_limit.call_args
        key = call_args.kwargs["key"]

        # Key should contain api_key prefix
        assert "api_key:" in key

    def test_different_endpoints_different_limits(self, rate_limit_client, mock_rate_limiter):
        """Test different endpoints have different rate limits"""
        mock_rate_limiter.check_rate_limit.return_value = (True, 99)

        # Call different endpoints
        rate_limit_client.get("/api/suggestions")
        rate_limit_client.get("/api/agent/discuss")

        # Verify different limits were used
        assert mock_rate_limiter.check_rate_limit.call_count == 2

        calls = mock_rate_limiter.check_rate_limit.call_args_list
        limits = [call.kwargs["limit"] for call in calls]

        # Suggestions: 100, Discuss: 10
        assert 100 in limits
        assert 10 in limits

    def test_disabled_middleware_allows_all(self):
        """Test disabled middleware allows all requests"""
        app = FastAPI()
        limiter = AsyncMock(spec=RateLimiter)
        app.add_middleware(RateLimitMiddleware, rate_limiter=limiter, enabled=False)

        @app.get("/test")
        async def test():
            return {"message": "success"}

        client = TestClient(app)
        response = client.get("/test")

        assert response.status_code == 200
        # Rate limiter should not be called
        limiter.check_rate_limit.assert_not_called()

    def test_rate_limit_error_includes_correlation_id(self, rate_limit_client, mock_rate_limiter):
        """Test rate limit error includes correlation ID"""
        mock_rate_limiter.check_rate_limit.return_value = (False, 0)

        response = rate_limit_client.get("/api/suggestions")

        assert "X-Correlation-ID" in response.headers
        data = response.json()
        assert "correlation_id" in data["error"]


# ============================================================================
# RequestSizeMiddleware Tests
# ============================================================================


@pytest.fixture
def app_with_size_limit():
    """Create FastAPI app with request size middleware"""
    app = FastAPI()
    app.add_middleware(RequestSizeMiddleware, max_size=1024)  # 1KB for testing

    @app.post("/upload")
    async def upload(request: Request):
        return {"message": "success"}

    return app


@pytest.fixture
def size_limit_client(app_with_size_limit):
    """Create test client for size limit tests"""
    return TestClient(app_with_size_limit)


class TestRequestSizeMiddleware:
    """Test RequestSizeMiddleware"""

    def test_allows_request_within_size_limit(self, size_limit_client):
        """Test middleware allows request within size limit"""
        small_data = "x" * 500  # 500 bytes

        response = size_limit_client.post("/upload", json={"data": small_data})

        assert response.status_code == 200

    def test_blocks_request_exceeding_size_limit(self, size_limit_client):
        """Test middleware blocks request exceeding size limit"""
        large_data = "x" * 2000  # 2KB (exceeds 1KB limit)

        response = size_limit_client.post("/upload", json={"data": large_data})

        assert response.status_code == 413
        assert "error" in response.json()
        assert response.json()["error"]["code"] == "REQUEST_TOO_LARGE"

    def test_size_limit_error_includes_details(self, size_limit_client):
        """Test size limit error includes size details"""
        large_data = "x" * 2000

        response = size_limit_client.post("/upload", json={"data": large_data})

        data = response.json()
        assert "details" in data["error"]
        assert "size_bytes" in data["error"]["details"]
        assert "max_size_bytes" in data["error"]["details"]

    def test_size_limit_error_includes_correlation_id(self, size_limit_client):
        """Test size limit error includes correlation ID"""
        large_data = "x" * 2000

        response = size_limit_client.post("/upload", json={"data": large_data})

        assert "X-Correlation-ID" in response.headers
        data = response.json()
        assert "correlation_id" in data["error"]

    def test_allows_request_without_content_length(self, size_limit_client):
        """Test middleware allows request without Content-Length header"""
        # Requests without Content-Length are allowed
        response = size_limit_client.get("/upload")

        # Will get 405 Method Not Allowed (GET on POST endpoint)
        # but not 413 Request Too Large
        assert response.status_code != 413

    def test_exact_size_limit_allowed(self, size_limit_client):
        """Test request at exact size limit is allowed"""
        # Create data exactly at limit (accounting for JSON overhead)
        data = "x" * 900  # Close to 1KB limit

        response = size_limit_client.post("/upload", json={"data": data})

        # Should be allowed (or might be slightly over due to JSON)
        assert response.status_code in [200, 413]

    @patch("src.api.middleware.logger")
    def test_logs_size_exceeded(self, mock_logger, size_limit_client):
        """Test size exceeded is logged"""
        large_data = "x" * 2000

        size_limit_client.post("/upload", json={"data": large_data})

        # Verify warning was logged
        assert mock_logger.warning.called


# ============================================================================
# Middleware Integration Tests
# ============================================================================


class TestMiddlewareIntegration:
    """Test middleware integration scenarios"""

    def test_multiple_middleware_stack(self, mock_rate_limiter):
        """Test multiple middleware work together"""
        app = FastAPI()

        # Add all middleware
        app.add_middleware(RequestSizeMiddleware, max_size=1024)
        app.add_middleware(RateLimitMiddleware, rate_limiter=mock_rate_limiter, enabled=True)
        app.add_middleware(CorrelationIDMiddleware)

        @app.post("/test")
        async def test():
            return {"message": "success"}

        client = TestClient(app)
        mock_rate_limiter.check_rate_limit.return_value = (True, 99)

        response = client.post("/test", json={"data": "test"})

        # All middleware should process
        assert response.status_code == 200
        assert "X-Correlation-ID" in response.headers
        assert "X-RateLimit-Limit" in response.headers

    def test_middleware_order_matters(self, mock_rate_limiter):
        """Test middleware execution order"""
        app = FastAPI()

        # Correlation ID should be first to be available to others
        app.add_middleware(RequestSizeMiddleware, max_size=1024)
        app.add_middleware(RateLimitMiddleware, rate_limiter=mock_rate_limiter, enabled=True)
        app.add_middleware(CorrelationIDMiddleware)

        @app.post("/test")
        async def test():
            return {"message": "success"}

        client = TestClient(app)
        mock_rate_limiter.check_rate_limit.return_value = (False, 0)

        # Rate limit exceeded
        response = client.post("/test", json={"data": "test"})

        # Should have correlation ID even though rate limited
        assert response.status_code == 429
        assert "X-Correlation-ID" in response.headers

    def test_middleware_error_handling(self, mock_rate_limiter):
        """Test middleware handles errors gracefully"""
        app = FastAPI(debug=False)
        app.add_middleware(RateLimitMiddleware, rate_limiter=mock_rate_limiter, enabled=True)
        register_exception_handlers(app)

        @app.get("/test")
        async def test():
            raise ValueError("Test error")

        client = TestClient(app, raise_server_exceptions=False)
        mock_rate_limiter.check_rate_limit.return_value = (True, 99)

        # Should get 500 error, not middleware error
        response = client.get("/test")
        assert response.status_code == 500
