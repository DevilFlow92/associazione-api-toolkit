# associazione-api-toolkit

Shared Python toolkit for the [associazione-api](https://github.com/DevilFlow92/associazione-api) ecosystem — resilient HTTP client, structured logging, pagination helpers, decorators and health checks.

[![CI](https://github.com/DevilFlow92/associazione-api-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/DevilFlow92/associazione-api-toolkit/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](LICENSE)

## Why this exists

The [associazione-api](https://github.com/DevilFlow92/associazione-api) backend needed reusable utilities that could live outside the main codebase — things like retry logic, structured logging, and pagination that any service in the ecosystem can import. Instead of copy-pasting helpers across repos, this toolkit packages them properly with tests, type hints, and semantic versioning.

## Modules

| Module | What it does |
|---|---|
| `associazione_toolkit.logging` | Structured JSON logging with request-id context propagation via `contextvars` |
| `associazione_toolkit.decorators` | `@retry` (exponential backoff), `@timed` (execution logging), `@validate_env` |
| `associazione_toolkit.pagination` | Offset-based and cursor-based pagination with Pydantic v2 models |
| `associazione_toolkit.http` | Async HTTP client with retry, timeout, and structured error handling |
| `associazione_toolkit.health` | Health check aggregator — polls `/health` endpoints concurrently |

## Install

```bash
pip install associazione-api-toolkit
```

Or with uv:

```bash
uv add associazione-api-toolkit
```

## Quick start

### Structured logging

```python
from associazione_toolkit.logging import configure_logging, get_logger, bind_request_id

configure_logging(level="INFO", render_json=True)
logger = get_logger(__name__)

bind_request_id("req-abc-123")
logger.info("member created", member_id=42)
# → {"event": "member created", "member_id": 42, "request_id": "req-abc-123", ...}
```

### Retry decorator

```python
from associazione_toolkit.decorators import retry

@retry(max_attempts=3, wait_seconds=0.5, exceptions=(ConnectionError,))
async def call_external_api() -> dict:
    ...
```

### Pagination

```python
from associazione_toolkit.pagination import PageParams, paginate

# In a FastAPI router:
@router.get("/soci/")
async def list_soci(params: PageParams = Depends()):
    items, total = await service.list(offset=params.offset, limit=params.limit)
    return paginate(items, total, params)
```

### Resilient HTTP client

```python
from associazione_toolkit.http import HttpClient

async with HttpClient(base_url="https://api.example.com", max_retries=3) as client:
    data = await client.get("/endpoint")
```

### Health checks

```python
from associazione_toolkit.health import HealthChecker

checker = HealthChecker(timeout=3.0)
result = await checker.check_all([
    "http://api-core:8000",
    "http://api-other:8001",
])
print(result.status)  # "healthy" | "degraded" | "unhealthy"
```

## Stack

| Layer | Technology |
|---|---|
| Language | Python 3.12+ |
| HTTP client | httpx |
| Validation | Pydantic v2 |
| Logging | structlog |
| Retry | tenacity |
| Build | Hatchling |
| Package manager | uv |
| Linting | Ruff |
| Type checking | mypy |
| Testing | pytest + pytest-asyncio + respx |

## Development

```bash
git clone https://github.com/DevilFlow92/associazione-api-toolkit.git
cd associazione-api-toolkit
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```

### Run tests

```bash
pytest tests/unit/ -v
```

### Lint & format

```bash
uv run ruff check --fix src/ tests/
uv run ruff format src/ tests/
```

### Type check

```bash
uv run mypy src/
```

## CI/CD

GitHub Actions runs on every push/PR to `main`:

- **Lint** — Ruff check + format
- **Type check** — mypy
- **Tests** — pytest on Python 3.12 & 3.13 with coverage

On tag `v*.*.*`, the release workflow builds the package and creates a GitHub Release.

## Related repositories

| Repository | Description |
|---|---|
| [associazione-api](https://github.com/DevilFlow92/associazione-api) | Core backend — FastAPI + PostgreSQL |
| [associazione-api-infra](https://github.com/DevilFlow92/associazione-api-infra) | Infrastructure — Helm charts + Kustomize for Kubernetes |
| **associazione-api-toolkit** | ← you are here |
