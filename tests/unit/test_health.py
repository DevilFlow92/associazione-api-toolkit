"""Unit tests for associazione_toolkit.health."""

import httpx
import pytest
import respx
from associazione_toolkit.health import (
    HealthChecker,
    HealthStatus,
    ServiceHealth,
    _aggregate_status,
)

# ---------------------------------------------------------------------------
# _aggregate_status
# ---------------------------------------------------------------------------


def test_aggregate_all_healthy() -> None:
    services = [
        ServiceHealth(url="http://a", status=HealthStatus.HEALTHY),
        ServiceHealth(url="http://b", status=HealthStatus.HEALTHY),
    ]
    assert _aggregate_status(services) == HealthStatus.HEALTHY


def test_aggregate_some_unhealthy() -> None:
    services = [
        ServiceHealth(url="http://a", status=HealthStatus.HEALTHY),
        ServiceHealth(url="http://b", status=HealthStatus.UNHEALTHY),
    ]
    assert _aggregate_status(services) == HealthStatus.DEGRADED


def test_aggregate_all_unhealthy() -> None:
    services = [
        ServiceHealth(url="http://a", status=HealthStatus.UNHEALTHY),
        ServiceHealth(url="http://b", status=HealthStatus.UNHEALTHY),
    ]
    assert _aggregate_status(services) == HealthStatus.UNHEALTHY


# ---------------------------------------------------------------------------
# HealthChecker.check_one
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_check_one_healthy() -> None:
    respx.get("http://api:8000/health").mock(
        return_value=httpx.Response(200, json={"status": "ok"})
    )
    checker = HealthChecker()
    result = await checker.check_one("http://api:8000")
    assert result.status == HealthStatus.HEALTHY
    assert result.response_ms is not None


@pytest.mark.asyncio
@respx.mock
async def test_check_one_unhealthy_5xx() -> None:
    respx.get("http://api:8000/health").mock(return_value=httpx.Response(503, json={}))
    checker = HealthChecker()
    result = await checker.check_one("http://api:8000")
    assert result.status == HealthStatus.UNHEALTHY
    assert result.detail == "HTTP 503"


@pytest.mark.asyncio
@respx.mock
async def test_check_one_timeout() -> None:
    respx.get("http://api:8000/health").mock(
        side_effect=httpx.TimeoutException("timed out")
    )
    checker = HealthChecker(timeout=1.0)
    result = await checker.check_one("http://api:8000")
    assert result.status == HealthStatus.UNHEALTHY
    assert result.detail == "timeout"


@pytest.mark.asyncio
@respx.mock
async def test_check_one_unreachable() -> None:
    respx.get("http://api:8000/health").mock(
        side_effect=httpx.ConnectError("unreachable")
    )
    checker = HealthChecker()
    result = await checker.check_one("http://api:8000")
    assert result.status == HealthStatus.UNHEALTHY
    assert result.detail is not None
    assert "unreachable" in result.detail


# ---------------------------------------------------------------------------
# HealthChecker.check_all
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
@respx.mock
async def test_check_all_all_healthy() -> None:
    respx.get("http://api-a:8000/health").mock(
        return_value=httpx.Response(200, json={})
    )
    respx.get("http://api-b:8001/health").mock(
        return_value=httpx.Response(200, json={})
    )
    checker = HealthChecker()
    result = await checker.check_all(["http://api-a:8000", "http://api-b:8001"])
    assert result.status == HealthStatus.HEALTHY
    assert result.healthy_count == 2
    assert result.unhealthy_count == 0


@pytest.mark.asyncio
@respx.mock
async def test_check_all_degraded() -> None:
    respx.get("http://api-a:8000/health").mock(
        return_value=httpx.Response(200, json={})
    )
    respx.get("http://api-b:8001/health").mock(
        return_value=httpx.Response(503, json={})
    )
    checker = HealthChecker()
    result = await checker.check_all(["http://api-a:8000", "http://api-b:8001"])
    assert result.status == HealthStatus.DEGRADED
    assert result.healthy_count == 1
    assert result.unhealthy_count == 1


@pytest.mark.asyncio
@respx.mock
async def test_check_all_unhealthy() -> None:
    respx.get("http://api-a:8000/health").mock(side_effect=httpx.ConnectError("down"))
    respx.get("http://api-b:8001/health").mock(side_effect=httpx.ConnectError("down"))
    checker = HealthChecker()
    result = await checker.check_all(["http://api-a:8000", "http://api-b:8001"])
    assert result.status == HealthStatus.UNHEALTHY
    assert result.unhealthy_count == 2


@pytest.mark.asyncio
@respx.mock
async def test_check_all_trailing_slash_stripped() -> None:
    respx.get("http://api:8000/health").mock(return_value=httpx.Response(200, json={}))
    checker = HealthChecker()
    result = await checker.check_all(["http://api:8000/"])
    assert result.status == HealthStatus.HEALTHY
