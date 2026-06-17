"""
Structured JSON logging with request-id and user-id context propagation.

Usage:
    from associazione_toolkit.logging import (
        get_logger,
        bind_request_id,
        bind_user_id,
    )

    logger = get_logger(__name__)
    logger.info("member created", member_id=42, action="create")

    # In a FastAPI middleware:
    bind_request_id("abc-123")
    logger.info("request started")  # → includes request_id automatically

    # In an auth dependency, once the principal is resolved:
    bind_user_id("user-42")
    logger.info("soci listed")  # → includes request_id and user_id automatically
"""

from __future__ import annotations

import logging
import sys
from contextvars import ContextVar
from typing import Any

import structlog

_request_id_var: ContextVar[str | None] = ContextVar("request_id", default=None)
_user_id_var: ContextVar[str | None] = ContextVar("user_id", default=None)


def bind_request_id(request_id: str) -> None:
    """Bind a request ID to the current async context."""
    _request_id_var.set(request_id)


def get_request_id() -> str | None:
    """Return the request ID bound to the current async context, if any."""
    return _request_id_var.get()


def bind_user_id(user_id: str) -> None:
    """Bind the authenticated principal's ID to the current async context.

    Call this once the user (or service account) is resolved — e.g. inside a
    FastAPI auth dependency — so every subsequent log line records *who* made
    the request, alongside the request_id.
    """
    _user_id_var.set(user_id)


def get_user_id() -> str | None:
    """Return the user ID bound to the current async context, if any."""
    return _user_id_var.get()


def _add_request_id(
    logger: Any,  # noqa: ANN401
    method: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """structlog processor: inject request_id from context if present."""
    request_id = _request_id_var.get()
    if request_id is not None:
        event_dict["request_id"] = request_id
    return event_dict


def _add_user_id(
    logger: Any,  # noqa: ANN401
    method: str,
    event_dict: dict[str, Any],
) -> dict[str, Any]:
    """structlog processor: inject user_id from context if present."""
    user_id = _user_id_var.get()
    if user_id is not None:
        event_dict["user_id"] = user_id
    return event_dict


def configure_logging(
    level: str = "INFO",
    render_json: bool = True,
) -> None:
    """
    Configure structlog for the entire application.

    Call once at startup (e.g. in main.py or app factory).

    Args:
        level: Standard log level string ("DEBUG", "INFO", "WARNING", "ERROR").
        render_json: If True renders JSON (production). If False renders
                     human-readable colored output (development).
    """
    shared_processors: list[Any] = [
        structlog.contextvars.merge_contextvars,
        _add_request_id,
        _add_user_id,
        structlog.stdlib.add_log_level,
        structlog.stdlib.add_logger_name,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
    ]

    if render_json:
        renderer: Any = structlog.processors.JSONRenderer()
    else:
        renderer = structlog.dev.ConsoleRenderer(colors=True)

    structlog.configure(
        processors=[
            *shared_processors,
            structlog.stdlib.ProcessorFormatter.wrap_for_formatter,
        ],
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    formatter = structlog.stdlib.ProcessorFormatter(
        foreign_pre_chain=shared_processors,
        processors=[
            structlog.stdlib.ProcessorFormatter.remove_processors_meta,
            renderer,
        ],
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(formatter)

    root_logger = logging.getLogger()
    root_logger.handlers = [handler]
    root_logger.setLevel(level.upper())


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """
    Return a named structlog logger.

    Args:
        name: Typically ``__name__`` of the calling module.

    Returns:
        A bound structlog logger instance.
    """
    return structlog.get_logger(name)
