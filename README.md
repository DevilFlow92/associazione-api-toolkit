# associazione-api-toolkit

Shared Python toolkit for the associazione-api ecosystem.

## Modules

- `toolkit.http` — resilient HTTP client with retry & backoff
- `toolkit.pagination` — cursor-based and offset pagination helpers
- `toolkit.logging` — structured JSON logger with request-id propagation
- `toolkit.decorators` — `@retry`, `@timed`, `@validate_env`
- `toolkit.health` — health check client & aggregator

## Install

```bash
pip install associazione-api-toolkit
```

## Development

```bash
uv venv && source .venv/bin/activate
uv pip install -e ".[dev]"
```
