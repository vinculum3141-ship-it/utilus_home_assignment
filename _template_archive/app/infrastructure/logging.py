"""Structured logging configuration."""

import logging
import sys
from typing import Any

import structlog

from app.infrastructure.settings import get_settings


def setup_logging() -> None:
    """Configure structured logging."""
    settings = get_settings()

    # Configure structlog
    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso"),
            structlog.processors.StackInfoRenderer(),
            structlog.processors.format_exc_info,
            structlog.processors.JSONRenderer()
            if settings.log_format == "json"
            else structlog.dev.ConsoleRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(
            logging.getLevelName(settings.log_level)
        ),
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, settings.log_level.upper()),
    )


def get_logger(name: str) -> Any:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (usually __name__)

    Returns:
        Structured logger
    """
    return structlog.get_logger(name)


# Convenience function for logging with context
def log_event(
    logger: Any, level: str, event: str, **kwargs: Any
) -> None:
    """
    Log an event with context.

    Args:
        logger: Logger instance
        level: Log level (info, warning, error, etc.)
        event: Event name
        **kwargs: Additional context
    """
    log_func = getattr(logger, level.lower())
    log_func(event, **kwargs)
