"""Unit tests for associazione_toolkit.logging."""

import json
from collections.abc import Iterator

import pytest
from associazione_toolkit.logging import (
    _add_request_id,
    _add_user_id,
    _request_id_var,
    _user_id_var,
    bind_request_id,
    bind_user_id,
    configure_logging,
    get_logger,
    get_request_id,
    get_user_id,
)


@pytest.fixture(autouse=True)
def _reset_context() -> Iterator[None]:
    """Reset the context vars before and after each test to avoid leakage."""
    _request_id_var.set(None)
    _user_id_var.set(None)
    yield
    _request_id_var.set(None)
    _user_id_var.set(None)


# ---------------------------------------------------------------------------
# request_id binding
# ---------------------------------------------------------------------------


def test_request_id_defaults_to_none() -> None:
    assert get_request_id() is None


def test_bind_and_get_request_id() -> None:
    bind_request_id("req-123")
    assert get_request_id() == "req-123"


# ---------------------------------------------------------------------------
# user_id binding
# ---------------------------------------------------------------------------


def test_user_id_defaults_to_none() -> None:
    assert get_user_id() is None


def test_bind_and_get_user_id() -> None:
    bind_user_id("user-42")
    assert get_user_id() == "user-42"


# ---------------------------------------------------------------------------
# processors
# ---------------------------------------------------------------------------


def test_add_request_id_processor_injects_when_bound() -> None:
    bind_request_id("req-xyz")
    event = _add_request_id(None, "info", {"event": "hello"})
    assert event["request_id"] == "req-xyz"


def test_add_request_id_processor_skips_when_unbound() -> None:
    event = _add_request_id(None, "info", {"event": "hello"})
    assert "request_id" not in event


def test_add_user_id_processor_injects_when_bound() -> None:
    bind_user_id("user-7")
    event = _add_user_id(None, "info", {"event": "hello"})
    assert event["user_id"] == "user-7"


def test_add_user_id_processor_skips_when_unbound() -> None:
    event = _add_user_id(None, "info", {"event": "hello"})
    assert "user_id" not in event


# ---------------------------------------------------------------------------
# configure_logging — end-to-end JSON rendering
# ---------------------------------------------------------------------------


def test_configure_logging_json_includes_context(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(level="INFO", render_json=True)
    bind_request_id("req-abc")
    bind_user_id("user-99")

    get_logger("test").info("member created", member_id=42)

    line = capsys.readouterr().out.strip().splitlines()[-1]
    payload = json.loads(line)

    assert payload["event"] == "member created"
    assert payload["member_id"] == 42
    assert payload["request_id"] == "req-abc"
    assert payload["user_id"] == "user-99"


def test_configure_logging_console_renderer_emits_output(
    capsys: pytest.CaptureFixture[str],
) -> None:
    configure_logging(level="DEBUG", render_json=False)
    get_logger("test").info("hello world")

    out = capsys.readouterr().out
    assert "hello world" in out
