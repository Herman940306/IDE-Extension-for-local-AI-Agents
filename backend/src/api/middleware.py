"""
Middleware Layer for FastAPI
Project Creator: Herman Swanepoel

Request/response processing pipeline including correlation ID, rate limiting, and size validation.  # noqa: E501
"""

import logging
import time
import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from src.services.rate_limiter import RateLimiter

logger = logging.getLogger(__name__)


class CorrelationIDMiddleware(BaseHTTPMiddleware):
    """Inject correlation ID into requests for tracing"""

    async def dispatch(self, request: Request, call_next):
        """
        Process request and inject correlation ID.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response with correlation ID header
        """
        # Extract or generate correlation ID
        correlation_id = request.headers.get("X-Correlation-ID", str(uuid.uuid4()))

        # Store in request state
        request.state.correlation_id = correlation_id

        # Log request
        logger.info(
            f"Request received: {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "client": request.client.host if request.client else "unknown",
            },
        )

        # Process request
        start_time = time.time()
        response = await call_next(request)
        duration_ms = (time.time() - start_time) * 1000

        # Add correlation ID to response
        response.headers["X-Correlation-ID"] = correlation_id

        # Log response
        logger.info(
            f"Request completed: {request.method} {request.url.path}",
            extra={
                "correlation_id": correlation_id,
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "duration_ms": duration_ms,
            },
        )

        return response


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Enforce rate limits on requests"""

    def __init__(self, app, rate_limiter: RateLimiter, enabled: bool = True):
        """
        Initialize rate limit middleware.

        Args:
            app: FastAPI application
            rate_limiter: RateLimiter service instance
            enabled: Whether rate limiting is enabled
        """
        super().__init__(app)
        self.rate_limiter = rate_limiter
        self.enabled = enabled

        # Per-endpoint rate limits (requests per minute)
        self.endpoint_limits = {
            "/api/suggestions": (100, 60),  # 100 req/min
            "/api/agent/discuss": (10, 60),  # 10 req/min
            "/api/analytics": (50, 60),  # 50 req/min
        }

    async def dispatch(self, request: Request, call_next):
        """
        Process request and enforce rate limits.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response or 429 if rate limit exceeded
        """
        if not self.enabled:
            return await call_next(request)

        # Extract client identifier (IP or API key)
        client_id = request.client.host if request.client else "unknown"
        api_key = request.headers.get("X-API-Key")
        if api_key:
            client_id = f"api_key:{api_key}"

        # Get rate limit for endpoint
        path = request.url.path
        limit, window = self.endpoint_limits.get(path, (100, 60))

        # Check rate limit
        allowed, remaining = await self.rate_limiter.check_rate_limit(
            key=f"{client_id}:{path}", limit=limit, window=window
        )

        if not allowed:
            correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))

            return JSONResponse(
                status_code=429,
                content={
                    "error": {
                        "code": "RATE_LIMIT_EXCEEDED",
                        "message": f"Rate limit exceeded: {limit} requests per {window} seconds",  # noqa: E501
                        "correlation_id": correlation_id,
                        "details": {"limit": limit, "window": window},
                    }
                },
                headers={
                    "Retry-After": str(window),
                    "X-RateLimit-Limit": str(limit),
                    "X-RateLimit-Remaining": "0",
                    "X-Correlation-ID": correlation_id,
                },
            )

        # Process request
        response = await call_next(request)

        # Add rate limit headers
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(remaining)

        return response


class RequestSizeMiddleware(BaseHTTPMiddleware):
    """Enforce request size limits"""

    def __init__(self, app, max_size: int = 10 * 1024 * 1024):  # 10MB default
        """
        Initialize request size middleware.

        Args:
            app: FastAPI application
            max_size: Maximum request size in bytes
        """
        super().__init__(app)
        self.max_size = max_size

        logger.info(
            "Request size middleware initialized",
            extra={"max_size_bytes": max_size, "max_size_mb": max_size / (1024 * 1024)},
        )

    async def dispatch(self, request: Request, call_next):
        """
        Process request and enforce size limits.

        Args:
            request: Incoming request
            call_next: Next middleware in chain

        Returns:
            Response or 413 if size exceeded
        """
        # Check Content-Length header
        content_length = request.headers.get("content-length")

        if content_length:
            size = int(content_length)

            if size > self.max_size:
                correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))

                logger.warning(
                    f"Request size exceeded: {size} bytes",
                    extra={
                        "correlation_id": correlation_id,
                        "size_bytes": size,
                        "max_size_bytes": self.max_size,
                        "path": request.url.path,
                    },
                )

                return JSONResponse(
                    status_code=413,
                    content={
                        "error": {
                            "code": "REQUEST_TOO_LARGE",
                            "message": f"Request too large. Max size: {self.max_size} bytes ({self.max_size / (1024 * 1024):.1f} MB)",  # noqa: E501
                            "correlation_id": correlation_id,
                            "details": {
                                "size_bytes": size,
                                "max_size_bytes": self.max_size,
                            },
                        }
                    },
                    headers={"X-Correlation-ID": correlation_id},
                )

        return await call_next(request)
