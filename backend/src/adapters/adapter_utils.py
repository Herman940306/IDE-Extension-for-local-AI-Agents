"""
Shared Adapter Utilities
Project Creator: Herman Swanepoel

Centralized utility functions for common adapter operations including
exponential backoff, response validation, and health checks.
"""

import asyncio
import logging
import random
import time
import uuid
from datetime import datetime
from functools import wraps
from typing import Any, Callable, Dict, List, Optional

from src.models import ConfidenceLevel
from src.utils.exceptions import ValidationException

logger = logging.getLogger(__name__)


class AdapterExceptions:
    """Centralized exception hierarchy for adapters"""

    class AdapterError(Exception):
        """Base exception for all adapter errors"""

    class AdapterInitializationError(AdapterError):
        """Raised when adapter initialization fails"""

    class AdapterExecutionError(AdapterError):
        """Raised when adapter execution fails"""

    class AdapterTimeoutError(AdapterError):
        """Raised when adapter operation times out"""

    class AdapterConnectionError(AdapterError):
        """Raised when adapter connection fails"""

    class AdapterAuthenticationError(AdapterError):
        """Raised when adapter authentication fails"""


class AdapterUtils:
    """Shared utilities for agent adapters"""

    @staticmethod
    def extract_code_blocks(text: str) -> List[tuple[str, str]]:
        """
        Extract code blocks from markdown-formatted text.

        Args:
            text: Text containing code blocks in markdown format

        Returns:
            List of tuples (code, description) where description is text before the code block  # noqa: E501
        """
        import re

        blocks = []
        # Match markdown code blocks with optional language identifier
        pattern = r"```(?:\w+)?\n(.*?)```"
        matches = re.finditer(pattern, text, re.DOTALL)

        for match in matches:
            code = match.group(1).strip()
            # Get text before this code block as description
            start_pos = match.start()
            # Look backwards for description (text before code block)
            text_before = text[:start_pos].strip()

            # Get last paragraph before code block
            paragraphs = text_before.split("\n\n")
            description = paragraphs[-1].strip() if paragraphs else "Code suggestion"

            if not description:
                description = "Code suggestion"

            blocks.append((code, description))

        return blocks

    @staticmethod
    def calculate_base_confidence(status: str, has_suggestions: bool, success_rate: float) -> float:
        """
        Calculate base confidence score for adapter response.

        Args:
            status: Task status (completed, failed, partial, etc.)
            has_suggestions: Whether suggestions were generated
            success_rate: Success rate of execution steps (0.0 to 1.0)

        Returns:
            Confidence score between 0.0 and 1.0
        """
        # Base confidence from status
        if status == "completed":
            base_confidence = 1.0
        elif status == "failed":
            base_confidence = 0.5
        elif status == "partial":
            base_confidence = 0.7
        else:
            base_confidence = 0.6

        # For completed tasks with suggestions and perfect success rate
        if status == "completed" and has_suggestions and success_rate == 1.0:
            return 1.0

        # For failed tasks with no suggestions and zero success rate
        if status == "failed" and not has_suggestions and success_rate == 0.0:
            return 0.5

        # For other cases, adjust by success rate
        # For completed status, maintain high confidence even with lower success rate
        if status == "completed":
            final_confidence = 0.75 + (success_rate * 0.25)  # Range: 0.75-1.0
        else:
            # Weight the confidence: 50% from status, 50% from success rate
            final_confidence = base_confidence * 0.5 + success_rate * 0.5

        # Apply suggestion penalty/boost
        if has_suggestions:
            final_confidence *= 1.0  # No penalty for having suggestions
        else:
            final_confidence *= 0.9  # Small penalty for no suggestions

        # Ensure within bounds
        return max(0.0, min(1.0, final_confidence))

    @staticmethod
    def format_reasoning_steps(steps: List[Dict[str, Any]], max_steps: int = 10) -> str:
        """
        Format reasoning steps into readable text.

        Args:
            steps: List of step dictionaries with tool, thought, status
            max_steps: Maximum number of steps to display

        Returns:
            Formatted string describing the reasoning process
        """
        if not steps:
            return "No execution steps recorded"

        total_steps = len(steps)
        displayed_steps = steps[:max_steps]

        lines = [f"Executed {total_steps} steps:"]

        for i, step in enumerate(displayed_steps, 1):
            tool = step.get("tool", "unknown")
            thought = step.get("thought", "")
            status = step.get("status", "unknown")

            status_symbol = "✓" if status in ["success", "completed"] else "✗"
            lines.append(f"{i}. [{status_symbol}] {tool}: {thought}")

        if total_steps > max_steps:
            remaining = total_steps - max_steps
            lines.append(f"... and {remaining} more steps")

        return "\n".join(lines)

    @staticmethod
    def truncate_output(output: str, max_length: int = 1000) -> str:
        """
        Truncate output to maximum length.

        Args:
            output: Output text to truncate
            max_length: Maximum length in characters

        Returns:
            Truncated output with ellipsis if needed
        """
        if len(output) <= max_length:
            return output

        return output[:max_length] + "..."

    @staticmethod
    def generate_suggestion_id(prefix: str = "sugg") -> str:
        """Generate a short unique identifier for suggestions."""
        return f"{prefix}-{uuid.uuid4().hex[:8]}"

    @staticmethod
    def map_confidence_score(score: float) -> ConfidenceLevel:
        """Map a numeric score to a discrete confidence level."""
        if score >= 0.75:
            return ConfidenceLevel.HIGH
        if score >= 0.4:
            return ConfidenceLevel.MEDIUM
        return ConfidenceLevel.LOW

    @staticmethod
    def calculate_step_success_rate(steps: List[Dict[str, Any]]) -> float:
        """
        Calculate success rate from execution steps.

        Args:
            steps: List of step dictionaries with status field

        Returns:
            Success rate between 0.0 and 1.0
        """
        if not steps:
            return 0.0

        success_count = 0
        for step in steps:
            status = step.get("status", "").lower()
            if status in ["success", "completed"]:
                success_count += 1

        return success_count / len(steps)

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
        response: Dict[str, Any],
        required_fields: List[str],
        adapter_name: str = "unknown",
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
                message=f"Response missing required fields: {', '.join(missing_fields)}",  # noqa: E501
                field="response",
                details={
                    "adapter": adapter_name,
                    "missing_fields": missing_fields,
                    "received_fields": list(response.keys()),
                },
            )

        logger.debug(
            "Response validation successful",
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
                extra={
                    "service": service_name,
                    "duration_ms": duration_ms,
                    "result": result,
                },
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
                extra={
                    "service": service_name,
                    "error": str(e),
                    "error_type": type(e).__name__,
                },
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
            logger.info(
                f"Adapter operation succeeded: {adapter_name}.{operation}",
                extra=log_data,
            )
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
