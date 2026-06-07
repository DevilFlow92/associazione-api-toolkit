"""
Resilient async HTTP client with retry, timeout and structured logging.

Built on httpx with tenacity retry logic. Designed to wrap external service
calls (e.g. from associazione-api-core to third-party endpoints).

Usage:
    from associazione_toolkit.http import HttpClient

    async with HttpClient(base_url="https://api.example.com") as client:
        data = await client.get("/endpoint", params={"q": "test"})

    # Or as a long-lived instance (e.g. FastAPI lifespan):
    client = HttpClient(base_url="https://api.example.com", timeout=10.0)
    await client.start()
    data = await client.post("/items", json={"name": "test"})
    await client.stop()
"""

from __future__ import annotations

from types import TracebackType
from typing import Any

import httpx

from associazione_toolkit.logging import get_logger

logger = get_logger(__name__)

DEFAULT_TIMEOUT = 10.0
DEFAULT_MAX_RETRIES = 3
DEFAULT_BACKOFF = 1.0


class HttpClientError(Exception):
    """Raised when an HTTP request fails after all retries."""

    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class HttpClient:
    """
    Async HTTP client with retry, timeout and structured logging.

    Args:
        base_url: Base URL prepended to every request path.
        timeout: Request timeout in seconds.
        max_retries: Number of retry attempts on transient errors.
        backoff_seconds: Base wait time between retries (exponential).
        headers: Default headers added to every request.
    """

    def __init__(
        self,
        base_url: str = "",
        timeout: float = DEFAULT_TIMEOUT,
        max_retries: int = DEFAULT_MAX_RETRIES,
        backoff_seconds: float = DEFAULT_BACKOFF,
        headers: dict[str, str] | None = None,
    ) -> None:
        self._base_url = base_url
        self._timeout = timeout
        self._max_retries = max_retries
        self._backoff_seconds = backoff_seconds
        self._default_headers = headers or {}
        self._client: httpx.AsyncClient | None = None

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------

    async def start(self) -> None:
        """Initialize the underlying httpx.AsyncClient."""
        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            timeout=self._timeout,
            headers=self._default_headers,
        )

    async def stop(self) -> None:
        """Close the underlying httpx.AsyncClient."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def __aenter__(self) -> HttpClient:
        await self.start()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: TracebackType | None,
    ) -> None:
        await self.stop()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    @property
    def _active_client(self) -> httpx.AsyncClient:
        if self._client is None:
            raise RuntimeError(
                "HttpClient is not started. "
                "Use 'async with HttpClient(...) as client' or call await client.start() first."
            )
        return self._client

    async def _request(
        self,
        method: str,
        path: str,
        **kwargs: Any,
    ) -> Any:
        """Execute an HTTP request with retry logic and structured logging."""
        attempt = 0
        last_exc: Exception | None = None

        while attempt < self._max_retries:
            attempt += 1
            try:
                logger.debug(
                    "http request",
                    method=method,
                    path=path,
                    attempt=attempt,
                )
                response = await self._active_client.request(method, path, **kwargs)
                response.raise_for_status()

                logger.info(
                    "http response",
                    method=method,
                    path=path,
                    status_code=response.status_code,
                    attempt=attempt,
                )
                return response.json()

            except httpx.HTTPStatusError as exc:
                status_code = exc.response.status_code
                # Do not retry 4xx client errors
                if 400 <= status_code < 500:
                    logger.warning(
                        "http client error",
                        method=method,
                        path=path,
                        status_code=status_code,
                    )
                    raise HttpClientError(
                        f"HTTP {status_code} for {method} {path}",
                        status_code=status_code,
                    ) from exc
                last_exc = exc
                logger.warning(
                    "http server error, will retry",
                    method=method,
                    path=path,
                    status_code=status_code,
                    attempt=attempt,
                    max_retries=self._max_retries,
                )

            except httpx.TransportError as exc:
                last_exc = exc
                logger.warning(
                    "http transport error, will retry",
                    method=method,
                    path=path,
                    error=str(exc),
                    attempt=attempt,
                    max_retries=self._max_retries,
                )

            # Exponential backoff between retries
            if attempt < self._max_retries:
                import asyncio

                wait = self._backoff_seconds * (2 ** (attempt - 1))
                await asyncio.sleep(wait)

        raise HttpClientError(
            f"Request failed after {self._max_retries} attempts: {method} {path}",
        ) from last_exc

    # ------------------------------------------------------------------
    # Public interface
    # ------------------------------------------------------------------

    async def get(self, path: str, params: dict[str, Any] | None = None) -> Any:
        """Send a GET request and return the parsed JSON response."""
        return await self._request("GET", path, params=params)

    async def post(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """Send a POST request with a JSON body and return the parsed JSON response."""
        return await self._request("POST", path, json=json)

    async def patch(self, path: str, json: dict[str, Any] | None = None) -> Any:
        """Send a PATCH request with a JSON body and return the parsed JSON response."""
        return await self._request("PATCH", path, json=json)

    async def delete(self, path: str) -> None:
        """Send a DELETE request. Returns None on success."""
        await self._request("DELETE", path)
