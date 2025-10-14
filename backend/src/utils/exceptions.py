"""
Exception Hierarchy for AuraIA Backend
Project Creator: Herman Swanepoel

Standardized exception handling with context tracking and correlation IDs.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional


class AuraIAException(Exception):
    """Base exception for all AuraIA errors"""

    def __init__(
        self,
        message: str,
        error_code: str,
        details: Optional[Dict[str, Any]] = None,
        correlation_id: Optional[str] = None,
    ):
        """
        Initialize AuraIA exception.

        Args:
            message: Human-readable error message
            error_code: Machine-readable error code
            details: Additional error context
            correlation_id: Request correlation ID for tracing
        """
        super().__init__(message)
        self.message = message
        self.error_code = error_code
        self.details = details or {}
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.timestamp = datetime.utcnow().isoformat()

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert exception to dictionary for API responses.

        Returns:
            Dictionary with error details
        """
        return {
            "error": {
                "code": self.error_code,
                "message": self.message,
                "details": self.details,
                "correlation_id": self.correlation_id,
                "timestamp": self.timestamp,
            }
        }

    def __str__(self) -> str:
        return f"[{self.error_code}] {self.message} (correlation_id: {self.correlation_id})"


class AdapterException(AuraIAException):
    """Adapter-specific errors"""

    def __init__(
        self, message: str, adapter_name: str, details: Optional[Dict[str, Any]] = None, **kwargs
    ):
        """
        Initialize adapter exception.

        Args:
            message: Error message
            adapter_name: Name of the adapter that failed
            details: Additional context
            **kwargs: Additional arguments for base class
        """
        adapter_details = {"adapter": adapter_name}
        if details:
            adapter_details.update(details)

        super().__init__(
            message=message, error_code="ADAPTER_ERROR", details=adapter_details, **kwargs
        )


class LLMException(AuraIAException):
    """LLM inference errors"""

    def __init__(
        self, message: str, model: str, details: Optional[Dict[str, Any]] = None, **kwargs
    ):
        """
        Initialize LLM exception.

        Args:
            message: Error message
            model: Model name that failed
            details: Additional context
            **kwargs: Additional arguments for base class
        """
        llm_details = {"model": model}
        if details:
            llm_details.update(details)

        super().__init__(message=message, error_code="LLM_ERROR", details=llm_details, **kwargs)


class ValidationException(AuraIAException):
    """Input validation errors"""

    def __init__(
        self, message: str, field: str, details: Optional[Dict[str, Any]] = None, **kwargs
    ):
        """
        Initialize validation exception.

        Args:
            message: Error message
            field: Field that failed validation
            details: Additional context
            **kwargs: Additional arguments for base class
        """
        validation_details = {"field": field}
        if details:
            validation_details.update(details)

        super().__init__(
            message=message, error_code="VALIDATION_ERROR", details=validation_details, **kwargs
        )


class CircuitBreakerOpenException(AuraIAException):
    """Circuit breaker is open"""

    def __init__(self, service_name: str, details: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize circuit breaker exception.

        Args:
            service_name: Name of the service with open circuit
            details: Additional context
            **kwargs: Additional arguments for base class
        """
        cb_details = {"service": service_name}
        if details:
            cb_details.update(details)

        super().__init__(
            message=f"Circuit breaker open for {service_name}",
            error_code="CIRCUIT_BREAKER_OPEN",
            details=cb_details,
            **kwargs,
        )


class RateLimitExceededException(AuraIAException):
    """Rate limit exceeded"""

    def __init__(self, limit: int, window: int, details: Optional[Dict[str, Any]] = None, **kwargs):
        """
        Initialize rate limit exception.

        Args:
            limit: Request limit
            window: Time window in seconds
            details: Additional context
            **kwargs: Additional arguments for base class
        """
        rl_details = {"limit": limit, "window": window}
        if details:
            rl_details.update(details)

        super().__init__(
            message=f"Rate limit exceeded: {limit} requests per {window} seconds",
            error_code="RATE_LIMIT_EXCEEDED",
            details=rl_details,
            **kwargs,
        )
