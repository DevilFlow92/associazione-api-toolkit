# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.2.0] - 2026-06-17

### Added
- `associazione_toolkit.logging` — `bind_user_id` / `get_user_id` propagate the
  authenticated principal into the async log context, so every log line emitted
  during an authenticated request records *who* made it alongside `request_id`.
  Complements the auth/RBAC layer added to the `associazione-api` backend.
- Unit tests for `associazione_toolkit.logging` (request-id, user-id and
  end-to-end JSON rendering).

## [0.1.0] - 2026-06-07

### Added
- `associazione_toolkit.logging` — structured JSON logging with request-id context propagation
- `associazione_toolkit.decorators` — `@retry`, `@timed`, `@validate_env` decorators
- `associazione_toolkit.pagination` — offset and cursor-based pagination helpers
- `associazione_toolkit.http` — resilient async HTTP client with retry and backoff
- `associazione_toolkit.health` — health check client and aggregator
- Test suite with 93%+ coverage
- CI/CD with GitHub Actions
