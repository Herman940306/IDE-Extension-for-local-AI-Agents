"""
Shared Adapter Utilities
Project Creator: Herman Swanepoel

Centralized utility functions for common adapter operations including
exponential backoff, response validation, and health checks.
"""

from typing import Callable, Any, Optional, Dict, List
import asyncio
import logging
import random
import time
from functools import wraps
from datetime import datetime

from src.utils.exceptions import ValidationException

logger = logging.getLogger(__name__)


class AdapterUtils:
    """Shared utilities for agent adapters"""

    @staticmethod
    async def exponential_backoff(
        func: Callable,
        max_retries: int = 3,
        base_delay: float = 1.0,
        max_delay: float = 60.0,
        exponential_base: float = 2.0,
        jitter: bool = True,
        *args,
        **kwargs,
    ) -> Any:
        """
        Execute function with exponential backoff retry logic.

        Args:
            func: Async function to execute
            max_retries: Maximum number of retry attempts
            base_delay: Initial delay in seconds
            max_delay: Maximum delay between retries
            exponential_base: Base for exponential calculation
            jitter: Add random jitter to prevent thundering herd
            *args: Positional arguments for func
            **kwargs: Keyword arguments for func

        Returns:
            Result from successful function execution

        Raises:
            Exception: Last exception if all retries exhausted
        """
        last_exception = None

        for attempt in range(max_retries + 1):
            try:
                start_time = time.time()
                result = await func(*args, **kwargs)
                duration_ms = (time.time() - start_time) * 1000

                if attempt > 0:
                    logger.info(
                        f"Function succeeded after {attempt} retries",
                        extra={
                            "function": func.__name__,
                            "attempt": attempt,
                            "duration_ms": duration_ms,
                        },
                    )

                return result

            except Exception as e:
                last_exception = e

                if attempt == max_retries:
                    logger.error(
                        f"Function failed after {max_retries} retries",
                        extra={
                            "function": func.__name__,
                            "max_retries": max_retries,
                            "error": str(e),
                        },
                    )
                    raise

                # Calculate delay with exponential backoff
                delay = min(base_delay * (exponential_base**attempt), max_delay)

                # Add jitter to prevent thundering herd
                if jitter:
                    delay = delay * (0.5 + random.random() * 0.5)

                logger.warning(
                    f"Function failed, retrying in {delay:.2f}s",
                    extra={
                        "function": func.__name__,
                        "attempt": attempt + 1,
                        "max_retries": max_retries,
                        "delay_seconds": delay,
                        "error": str(e),
                    },
                )

                await asyncio.sleep(delay)

        # This should never be reached, but just in case
        if last_exception:
            raise last_exception

    @staticmethod
    def validate_response(
        response: Dict[str, Any], required_fields: List[str], adapter_name: str = "unknown"
    ) -> Dict[str, Any]:
        """
        Validate adapter response structure.

        Args:
            response: Response dictionary from adapter
            required_fields: List of required field names
            adapter_name: Name of adapter for error messages

        Returns:
            Validated response dictionary

        Raises:
            ValidationException: If response is invalid
        """
        if not isinstance(response, dict):
            raise ValidationException(
                message=f"Response must be a dictionary, got {type(response).__name__}",
                field="response",
                details={"adapter": adapter_name},
            )

        missing_fields = []
        for field in required_fields:
            if field not in response:
                missing_fields.append(field)

        if missing_fields:
            raise ValidationException(
                message=f"Response missing required fields: {', '.join(missing_fields)}",
                field="response",
                details={
                    "adapter": adapter_name,
                    "missing_fields": missing_fields,
                    "received_fields": list(response.keys()),
                },
            )

        logger.debug(
            f"Response validation successful",
            extra={"adapter": adapter_name, "fields": list(response.keys())},
        )

        return response

    @staticmethod
    async def health_check_with_timeout(
        check_func: Callable, timeout: float = 5.0, service_name: str = "unknown"
    ) -> bool:
        """
        Execute health check with timeout protection.

        Args:
            check_func: Async health check function
            timeout: Timeout in seconds
            service_name: Name of service for logging

        Returns:
            True if healthy, False otherwise
        """
        try:
            start_time = time.time()
            result = await asyncio.wait_for(check_func(), timeout=timeout)
            duration_ms = (time.time() - start_time) * 1000

            logger.debug(
                f"Health check passed for {service_name}",
                extra={"service": service_name, "duration_ms": duration_ms, "result": result},
            )

            return bool(result)

        except asyncio.TimeoutError:
            logger.warning(
                f"Health check timeout for {service_name}",
                extra={"service": service_name, "timeout_seconds": timeout},
            )
            return False

        except Exception as e:
            logger.error(
                f"Health check failed for {service_name}",
                extra={"service": service_name, "error": str(e), "error_type": type(e).__name__},
            )
            return False

    @staticmethod
    def log_adapter_operation(
        adapter_name: str,
        operation: str,
        duration_ms: float,
        success: bool,
        error: Optional[Exception] = None,
        additional_context: Optional[Dict[str, Any]] = None,
    ) -> None:
        """
        Log adapter operation with structured logging.

        Args:
            adapter_name: Name of the adapter
            operation: Operation being performed
            duration_ms: Operation duration in milliseconds
            success: Whether operation succeeded
            error: Exception if operation failed
            additional_context: Additional context to log
        """
        log_data = {
            "adapter": adapter_name,
            "operation": operation,
            "duration_ms": duration_ms,
            "success": success,
            "timestamp": datetime.utcnow().isoformat(),
        }

        if additional_context:
            log_data.update(additional_context)

        if success:
            logger.info(f"Adapter operation succeeded: {adapter_name}.{operation}", extra=log_data)
        else:
            log_data["error"] = str(error) if error else "Unknown error"
            log_data["error_type"] = type(error).__name__ if error else "Unknown"

            logger.error(f"Adapter operation failed: {adapter_name}.{operation}", extra=log_data)


def with_retry(max_retries: int = 3, base_delay: float = 1.0, max_delay: float = 60.0):
    """
    Decorator for automatic retry with exponential backoff.

    Args:
        max_retries: Maximum number of retry attempts
        base_delay: Initial delay in seconds
        max_delay: Maximum delay between retries

    Returns:
        Decorated function with retry logic
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            return await AdapterUtils.exponential_backoff(
                func,
                max_retries=max_retries,
                base_delay=base_delay,
                max_delay=max_delay,
                *args,
                **kwargs,
            )

        return wrapper

    return decorator
