"""Unit tests for associazione_toolkit.http."""

import httpx
import pytest
import respx
from associazione_toolkit.http import HttpClient, HttpClientError

# ---------------------------------------------------------------------------
# Lifecycle
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_client_context_manager() -> None:
    async with HttpClient(base_url="http://test") as client:
        assert client._client is not None
    assert client._client is None


@pytest.mark.asyncio
async def test_client_not_started_raises() -> None:
    client = HttpClient(base_url="http://test")
    with pytest.raises(RuntimeError, match="not started"):
        await client.get("/path")


# ---------------------------------------------------------------------------
# GET
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_get_success() -> None:
    respx.get("http://test/items").mock(
        return_value=httpx.Response(200, json={"items": []})
    )
    async with HttpClient(base_url="http://test") as client:
        result = await client.get("/items")
    assert result == {"items": []}


@pytest.mark.asyncio
@respx.mock
async def test_get_with_params() -> None:
    respx.get("http://test/items", params={"q": "banda"}).mock(
        return_value=httpx.Response(200, json={"q": "banda"})
    )
    async with HttpClient(base_url="http://test") as client:
        result = await client.get("/items", params={"q": "banda"})
    assert result == {"q": "banda"}


# ---------------------------------------------------------------------------
# POST
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_post_success() -> None:
    respx.post("http://test/items").mock(
        return_value=httpx.Response(201, json={"id": 1})
    )
    async with HttpClient(base_url="http://test") as client:
        result = await client.post("/items", json={"name": "test"})
    assert result == {"id": 1}


# ---------------------------------------------------------------------------
# PATCH
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_patch_success() -> None:
    respx.patch("http://test/items/1").mock(
        return_value=httpx.Response(200, json={"id": 1, "name": "updated"})
    )
    async with HttpClient(base_url="http://test") as client:
        result = await client.patch("/items/1", json={"name": "updated"})
    assert result == {"id": 1, "name": "updated"}


# ---------------------------------------------------------------------------
# DELETE
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_delete_success() -> None:
    respx.delete("http://test/items/1").mock(return_value=httpx.Response(204, json={}))
    async with HttpClient(base_url="http://test") as client:
        result = await client.delete("/items/1")
    assert result is None


# ---------------------------------------------------------------------------
# Error handling
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_4xx_raises_immediately_no_retry() -> None:
    respx.get("http://test/items").mock(
        return_value=httpx.Response(404, json={"detail": "not found"})
    )
    async with HttpClient(base_url="http://test", max_retries=3) as client:
        with pytest.raises(HttpClientError) as exc_info:
            await client.get("/items")

    assert exc_info.value.status_code == 404


@pytest.mark.asyncio
@respx.mock
async def test_5xx_retries_and_raises() -> None:
    respx.get("http://test/items").mock(
        return_value=httpx.Response(500, json={"detail": "server error"})
    )
    async with HttpClient(
        base_url="http://test", max_retries=2, backoff_seconds=0.01
    ) as client:
        with pytest.raises(HttpClientError):
            await client.get("/items")

    assert respx.calls.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_transport_error_retries_and_raises() -> None:
    respx.get("http://test/items").mock(side_effect=httpx.ConnectError("unreachable"))

    async with HttpClient(
        base_url="http://test", max_retries=2, backoff_seconds=0.01
    ) as client:
        with pytest.raises(HttpClientError):
            await client.get("/items")

    assert respx.calls.call_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_retries_succeed_on_second_attempt() -> None:
    respx.get("http://test/items").mock(
        side_effect=[
            httpx.Response(503, json={}),
            httpx.Response(200, json={"ok": True}),
        ]
    )
    async with HttpClient(
        base_url="http://test", max_retries=3, backoff_seconds=0.01
    ) as client:
        result = await client.get("/items")

    assert result == {"ok": True}
    assert respx.calls.call_count == 2
