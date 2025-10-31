"""
Circuit Breaker Pattern Implementation
Project Creator: Herman Swanepoel

Prevents cascading failures when external services are unhealthy.
"""

import logging
from datetime import datetime, timedelta
from enum import Enum
from typing import Any, Callable, Dict, Optional

from src.utils.exceptions import CircuitBreakerOpenException

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    """Circuit breaker states"""

    CLOSED = "closed"  # Normal operation
    OPEN = "open"  # Failing, reject requests
    HALF_OPEN = "half_open"  # Testing recovery


class CircuitBreaker:
    """Circuit breaker for external service calls"""

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        timeout_seconds: float = 60.0,
        success_threshold: int = 2,
    ):
        """
        Initialize circuit breaker.

        Args:
            name: Circuit breaker name (for logging)
            failure_threshold: Failures before opening circuit
            timeout_seconds: Time to wait before half-open
            success_threshold: Successes needed to close from half-open
        """
        self.name = name
        self.failure_threshold = failure_threshold
        self.timeout = timedelta(seconds=timeout_seconds)
        self.success_threshold = success_threshold

        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time: Optional[datetime] = None
        self._last_state_change = datetime.utcnow()

        logger.info(
            f"Circuit breaker initialized: {name}",
            extra={
                "circuit_breaker": name,
                "failure_threshold": failure_threshold,
                "timeout_seconds": timeout_seconds,
                "success_threshold": success_threshold,
            },
        )

    async def call(self, func: Callable, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to execute
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from function execution

        Raises:
            CircuitBreakerOpenException: If circuit is open
            Exception: Original exception from func
        """
        # Check if we should attempt reset
        if self._state == CircuitState.OPEN and self._should_attempt_reset():
            self._transition_to_half_open()

        # Reject if circuit is open
        if self._state == CircuitState.OPEN:
            raise CircuitBreakerOpenException(
                service_name=self.name,
                details={
                    "failure_count": self._failure_count,
                    "last_failure": (
                        self._last_failure_time.isoformat() if self._last_failure_time else None
                    ),
                },
            )

        # Attempt the call
        try:
            result = await func(*args, **kwargs)
            self._on_success()
            return result

        except Exception:
            self._on_failure()
            raise

    def _should_attempt_reset(self) -> bool:
        """Check if circuit should transition to half-open"""
        if self._last_failure_time is None:
            return False

        time_since_failure = datetime.utcnow() - self._last_failure_time
        return time_since_failure >= self.timeout

    def _on_success(self) -> None:
        """Handle successful call"""
        if self._state == CircuitState.HALF_OPEN:
            self._success_count += 1

            logger.info(
                f"Circuit breaker success in half-open state: {self.name}",
                extra={
                    "circuit_breaker": self.name,
                    "success_count": self._success_count,
                    "success_threshold": self.success_threshold,
                },
            )

            if self._success_count >= self.success_threshold:
                self._transition_to_closed()

        elif self._state == CircuitState.CLOSED:
            # Reset failure count on success
            if self._failure_count > 0:
                self._failure_count = 0

    def _on_failure(self) -> None:
        """Handle failed call"""
        self._failure_count += 1
        self._last_failure_time = datetime.utcnow()

        logger.warning(
            f"Circuit breaker failure: {self.name}",
            extra={
                "circuit_breaker": self.name,
                "failure_count": self._failure_count,
                "failure_threshold": self.failure_threshold,
                "state": self._state.value,
            },
        )

        if self._state == CircuitState.HALF_OPEN:
            # Immediately reopen on failure in half-open
            self._transition_to_open()

        elif self._state == CircuitState.CLOSED:
            # Open if threshold exceeded (threshold of 0 means never open)
            if self.failure_threshold > 0 and self._failure_count >= self.failure_threshold:
                self._transition_to_open()

    def _transition_to_open(self) -> None:
        """Transition to OPEN state"""
        self._state = CircuitState.OPEN
        self._success_count = 0
        self._last_state_change = datetime.utcnow()

        logger.error(
            f"Circuit breaker opened: {self.name}",
            extra={
                "circuit_breaker": self.name,
                "failure_count": self._failure_count,
                "state": "open",
            },
        )

    def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state"""
        self._state = CircuitState.HALF_OPEN
        self._success_count = 0
        self._last_state_change = datetime.utcnow()

        logger.info(
            f"Circuit breaker half-open: {self.name}",
            extra={"circuit_breaker": self.name, "state": "half_open"},
        )

    def _transition_to_closed(self) -> None:
        """Transition to CLOSED state"""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_state_change = datetime.utcnow()

        logger.info(
            f"Circuit breaker closed: {self.name}",
            extra={"circuit_breaker": self.name, "state": "closed"},
        )

    def get_state(self) -> Dict[str, Any]:
        """
        Get current circuit breaker state.

        Returns:
            Dictionary with state information
        """
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "success_threshold": self.success_threshold,
            "last_failure_time": (
                self._last_failure_time.isoformat() if self._last_failure_time else None
            ),
            "last_state_change": self._last_state_change.isoformat(),
            "timeout_seconds": self.timeout.total_seconds(),
        }

    def reset(self) -> None:
        """Manually reset circuit breaker to closed state"""
        logger.info(
            f"Circuit breaker manually reset: {self.name}",
            extra={"circuit_breaker": self.name},
        )
        self._transition_to_closed()
