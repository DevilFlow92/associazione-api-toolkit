"""
Utility decorators for resilience, observability and environment validation.

Usage:
    from associazione_toolkit.decorators import retry, timed, validate_env

    @retry(max_attempts=3, wait_seconds=1.0)
    async def call_external_service() -> dict:
        ...

    @timed("fetch_members")
    async def fetch_members() -> list:
        ...

    @validate_env("DATABASE_URL", "SECRET_KEY")
    def create_app() -> FastAPI:
        ...
"""

from __future__ import annotations

import functools
import os
import time
from collections.abc import Callable
from typing import Any, TypeVar

from tenacity import (
    retry as tenacity_retry,
)
from tenacity import (
    retry_if_exception_type,
    stop_after_attempt,
    wait_exponential,
)

from associazione_toolkit.logging import get_logger

logger = get_logger(__name__)

F = TypeVar("F", bound=Callable[..., Any])


def retry(
    max_attempts: int = 3,
    wait_seconds: float = 1.0,
    exceptions: tuple[type[Exception], ...] = (Exception,),
) -> Callable[[F], F]:
    """
    Decorator that retries a function on failure with exponential backoff.

    Works with both sync and async functions.

    Args:
        max_attempts: Maximum number of attempts before giving up.
        wait_seconds: Base wait time in seconds between retries (doubles each time).
        exceptions: Tuple of exception types that trigger a retry.

    Example:
        @retry(max_attempts=3, wait_seconds=0.5, exceptions=(httpx.HTTPError,))
        async def fetch_data() -> dict:
            ...
    """

    def decorator(func: F) -> F:
        @tenacity_retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=wait_seconds, min=wait_seconds, max=30),
            retry=retry_if_exception_type(exceptions),
            reraise=True,
        )
        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            return await func(*args, **kwargs)

        @tenacity_retry(
            stop=stop_after_attempt(max_attempts),
            wait=wait_exponential(multiplier=wait_seconds, min=wait_seconds, max=30),
            retry=retry_if_exception_type(exceptions),
            reraise=True,
        )
        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            return func(*args, **kwargs)

        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


def timed(operation: str | None = None) -> Callable[[F], F]:
    """
    Decorator that logs the execution time of a function.

    Works with both sync and async functions.

    Args:
        operation: Label used in the log entry. Defaults to the function name.

    Example:
        @timed("fetch_members")
        async def get_all_members() -> list:
            ...
    """

    def decorator(func: F) -> F:
        label = operation or func.__name__

        @functools.wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                result = await func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.info(
                    "operation completed",
                    operation=label,
                    duration_ms=round(elapsed * 1000, 2),
                )
                return result
            except Exception:
                elapsed = time.perf_counter() - start
                logger.warning(
                    "operation failed",
                    operation=label,
                    duration_ms=round(elapsed * 1000, 2),
                )
                raise

        @functools.wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.perf_counter()
            try:
                result = func(*args, **kwargs)
                elapsed = time.perf_counter() - start
                logger.info(
                    "operation completed",
                    operation=label,
                    duration_ms=round(elapsed * 1000, 2),
                )
                return result
            except Exception:
                elapsed = time.perf_counter() - start
                logger.warning(
                    "operation failed",
                    operation=label,
                    duration_ms=round(elapsed * 1000, 2),
                )
                raise

        import inspect

        if inspect.iscoroutinefunction(func):
            return async_wrapper  # type: ignore[return-value]
        return sync_wrapper  # type: ignore[return-value]

    return decorator


def validate_env(*required_vars: str) -> Callable[[F], F]:
    """
    Decorator that validates required environment variables are set before
    the function executes. Raises ``EnvironmentError`` if any are missing.

    Args:
        *required_vars: Names of required environment variables.

    Example:
        @validate_env("DATABASE_URL", "SECRET_KEY")
        def create_app() -> FastAPI:
            ...
    """

    def decorator(func: F) -> F:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            missing = [var for var in required_vars if not os.environ.get(var)]
            if missing:
                raise OSError(
                    f"Missing required environment variables: {', '.join(missing)}"
                )
            return func(*args, **kwargs)

        return wrapper  # type: ignore[return-value]

    return decorator
