"""
Global Exception Handlers for FastAPI
Project Creator: Herman Swanepoel
"""

import uuid
from datetime import datetime

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from src.core.logging import get_logger
from src.utils.exceptions import AuraIAException, RateLimitExceededException

logger = get_logger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """
    Register global exception handlers for the FastAPI application.

    Args:
        app: FastAPI application instance
    """

    @app.exception_handler(RateLimitExceededException)
    async def rate_limit_exception_handler(
        request: Request, exc: RateLimitExceededException
    ) -> JSONResponse:
        """Handle rate limit exceeded exceptions"""
        logger.warning(
            "rate_limit_exceeded",
            correlation_id=exc.correlation_id,
            error_code=exc.error_code,
            path=str(request.url.path),
            client=request.client.host if request.client else "unknown",
        )
        return JSONResponse(
            status_code=429,
            content=exc.to_dict(),
            headers={
                "Retry-After": str(exc.details.get("window", 60)),
                "X-Correlation-ID": exc.correlation_id,
            },
        )

    @app.exception_handler(AuraIAException)
    async def aura_exception_handler(
        request: Request, exc: AuraIAException
    ) -> JSONResponse:
        """Handle all AuraIA exceptions"""
        logger.error(
            "aura_exception",
            correlation_id=exc.correlation_id,
            error_code=exc.error_code,
            path=str(request.url.path),
            method=request.method,
        )

        # Determine status code based on error type
        status_code = 500
        if exc.error_code == "VALIDATION_ERROR":
            status_code = 400
        elif exc.error_code == "CIRCUIT_BREAKER_OPEN":
            status_code = 503

        return JSONResponse(
            status_code=status_code,
            content=exc.to_dict(),
            headers={"X-Correlation-ID": exc.correlation_id},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        """Handle all unhandled exceptions"""
        correlation_id = getattr(request.state, "correlation_id", str(uuid.uuid4()))

        logger.error(
            "unhandled_exception",
            correlation_id=correlation_id,
            path=str(request.url.path),
            method=request.method,
            exception_type=type(exc).__name__,
            error=str(exc),
        )

        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "An unexpected error occurred",
                    "correlation_id": correlation_id,
                    "timestamp": datetime.utcnow().isoformat(),
                }
            },
            headers={"X-Correlation-ID": correlation_id},
        )
