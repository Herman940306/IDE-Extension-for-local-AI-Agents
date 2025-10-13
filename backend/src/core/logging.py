"""
Structured Logging Configuration
Project Creator: Herman Swanepoel
"""

import structlog


def configure_logging(log_level: str = "INFO") -> None:
    """Configure structured logging with JSON output"""
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            getattr(structlog.stdlib.logging, log_level.upper(), structlog.stdlib.logging.INFO)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.BoundLogger:
    """Get logger instance with context"""
    return structlog.get_logger(name)


def bind_correlation_id(correlation_id: str) -> None:
    """Bind correlation ID to context"""
    structlog.contextvars.bind_contextvars(correlation_id=correlation_id)


def clear_correlation_id() -> None:
    """Clear correlation ID from context"""
    structlog.contextvars.clear_contextvars()
