"""
Health check client and aggregator.

Polls /health endpoints of one or more services and aggregates results
into a single status. Useful in a gateway or orchestrator that needs to
report the health of the entire associazione-api ecosystem.

Usage:
    from associazione_toolkit.health import HealthChecker, ServiceHealth, OverallHealth

    checker = HealthChecker(timeout=3.0)
    result = await checker.check_all([
        "http://associazione-api:8000",
        "http://other-service:8001",
    ])

    print(result.status)       # "healthy" | "degraded" | "unhealthy"
    print(result.services)     # list of ServiceHealth
"""

from __future__ import annotations

import asyncio
from enum import StrEnum

import httpx
from pydantic import BaseModel

from associazione_toolkit.logging import get_logger

logger = get_logger(__name__)

HEALTH_PATH = "/health"


class HealthStatus(StrEnum):
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"


class ServiceHealth(BaseModel):
    """Health status of a single service."""

    url: str
    status: HealthStatus
    response_ms: float | None = None
    detail: str | None = None


class OverallHealth(BaseModel):
    """Aggregated health status across all checked services."""

    status: HealthStatus
    services: list[ServiceHealth]

    @property
    def healthy_count(self) -> int:
        return sum(1 for s in self.services if s.status == HealthStatus.HEALTHY)

    @property
    def unhealthy_count(self) -> int:
        return sum(1 for s in self.services if s.status == HealthStatus.UNHEALTHY)


def _aggregate_status(services: list[ServiceHealth]) -> HealthStatus:
    """Derive overall status from individual service statuses.

    - All healthy → healthy
    - Any healthy, some unhealthy → degraded
    - All unhealthy → unhealthy
    """
    statuses = {s.status for s in services}
    if statuses == {HealthStatus.HEALTHY}:
        return HealthStatus.HEALTHY
    if HealthStatus.HEALTHY in statuses:
        return HealthStatus.DEGRADED
    return HealthStatus.UNHEALTHY


class HealthChecker:
    """
    Async health check aggregator.

    Concurrently polls the /health endpoint of each registered service
    and returns an OverallHealth with individual and aggregate statuses.

    Args:
        timeout: Per-request timeout in seconds.
        health_path: Path to poll on each service (default: /health).
    """

    def __init__(
        self,
        timeout: float = 3.0,
        health_path: str = HEALTH_PATH,
    ) -> None:
        self._timeout = timeout
        self._health_path = health_path

    async def _check_one(
        self,
        client: httpx.AsyncClient,
        base_url: str,
    ) -> ServiceHealth:
        """Probe a single service's health endpoint."""
        url = base_url.rstrip("/") + self._health_path
        import time

        start = time.perf_counter()
        try:
            response = await client.get(url)
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)

            if response.status_code == 200:
                logger.debug("service healthy", url=base_url, response_ms=elapsed_ms)
                return ServiceHealth(
                    url=base_url,
                    status=HealthStatus.HEALTHY,
                    response_ms=elapsed_ms,
                )
            else:
                logger.warning(
                    "service unhealthy",
                    url=base_url,
                    status_code=response.status_code,
                )
                return ServiceHealth(
                    url=base_url,
                    status=HealthStatus.UNHEALTHY,
                    response_ms=elapsed_ms,
                    detail=f"HTTP {response.status_code}",
                )

        except httpx.TimeoutException:
            elapsed_ms = round((time.perf_counter() - start) * 1000, 2)
            logger.warning("service health check timed out", url=base_url)
            return ServiceHealth(
                url=base_url,
                status=HealthStatus.UNHEALTHY,
                response_ms=elapsed_ms,
                detail="timeout",
            )

        except httpx.TransportError as exc:
            logger.warning("service unreachable", url=base_url, error=str(exc))
            return ServiceHealth(
                url=base_url,
                status=HealthStatus.UNHEALTHY,
                detail=f"unreachable: {exc}",
            )

    async def check_all(self, base_urls: list[str]) -> OverallHealth:
        """
        Concurrently check all services and return aggregated health.

        Args:
            base_urls: List of service base URLs (e.g. "http://api:8000").

        Returns:
            OverallHealth with per-service results and aggregate status.
        """
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            tasks = [self._check_one(client, url) for url in base_urls]
            services = await asyncio.gather(*tasks)

        services_list = list(services)
        overall = _aggregate_status(services_list)

        logger.info(
            "health check completed",
            overall=overall,
            healthy=sum(1 for s in services_list if s.status == HealthStatus.HEALTHY),
            total=len(services_list),
        )

        return OverallHealth(status=overall, services=services_list)

    async def check_one(self, base_url: str) -> ServiceHealth:
        """
        Check a single service's health.

        Args:
            base_url: Service base URL (e.g. "http://api:8000").

        Returns:
            ServiceHealth for that service.
        """
        async with httpx.AsyncClient(timeout=self._timeout) as client:
            return await self._check_one(client, base_url)
