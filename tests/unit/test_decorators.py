"""Unit tests for associazione_toolkit.decorators."""

import pytest
from associazione_toolkit.decorators import retry, timed, validate_env

# ---------------------------------------------------------------------------
# @retry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_retry_succeeds_on_first_attempt() -> None:
    call_count = 0

    @retry(max_attempts=3)
    async def always_ok() -> str:
        nonlocal call_count
        call_count += 1
        return "ok"

    result = await always_ok()
    assert result == "ok"
    assert call_count == 1


@pytest.mark.asyncio
async def test_retry_succeeds_after_failures() -> None:
    call_count = 0

    @retry(max_attempts=3, wait_seconds=0.01)
    async def fails_twice() -> str:
        nonlocal call_count
        call_count += 1
        if call_count < 3:
            raise ValueError("transient error")
        return "recovered"

    result = await fails_twice()
    assert result == "recovered"
    assert call_count == 3


@pytest.mark.asyncio
async def test_retry_raises_after_max_attempts() -> None:
    call_count = 0

    @retry(max_attempts=2, wait_seconds=0.01)
    async def always_fails() -> None:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("permanent error")

    with pytest.raises(RuntimeError, match="permanent error"):
        await always_fails()

    assert call_count == 2


@pytest.mark.asyncio
async def test_retry_does_not_retry_excluded_exceptions() -> None:
    call_count = 0

    @retry(max_attempts=3, wait_seconds=0.01, exceptions=(ValueError,))
    async def raises_type_error() -> None:
        nonlocal call_count
        call_count += 1
        raise TypeError("not retried")

    with pytest.raises(TypeError):
        await raises_type_error()

    assert call_count == 1


def test_retry_sync_succeeds() -> None:
    call_count = 0

    @retry(max_attempts=3, wait_seconds=0.01)
    def sync_ok() -> str:
        nonlocal call_count
        call_count += 1
        return "ok"

    result = sync_ok()
    assert result == "ok"
    assert call_count == 1


def test_retry_sync_raises_after_max_attempts() -> None:
    call_count = 0

    @retry(max_attempts=2, wait_seconds=0.01)
    def sync_fails() -> None:
        nonlocal call_count
        call_count += 1
        raise RuntimeError("sync error")

    with pytest.raises(RuntimeError):
        sync_fails()

    assert call_count == 2


# ---------------------------------------------------------------------------
# @timed
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_timed_returns_result() -> None:
    @timed("test_op")
    async def compute() -> int:
        return 42

    result = await compute()
    assert result == 42


@pytest.mark.asyncio
async def test_timed_propagates_exception() -> None:
    @timed("failing_op")
    async def failing() -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError, match="boom"):
        await failing()


def test_timed_sync_returns_result() -> None:
    @timed("sync_op")
    def sync_compute() -> str:
        return "done"

    assert sync_compute() == "done"


def test_timed_sync_propagates_exception() -> None:
    @timed()
    def sync_failing() -> None:
        raise RuntimeError("sync boom")

    with pytest.raises(RuntimeError, match="sync boom"):
        sync_failing()


# ---------------------------------------------------------------------------
# @validate_env
# ---------------------------------------------------------------------------


def test_validate_env_passes_when_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MY_VAR", "value")

    @validate_env("MY_VAR")
    def fn() -> str:
        return "ok"

    assert fn() == "ok"


def test_validate_env_raises_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("MISSING_VAR", raising=False)

    @validate_env("MISSING_VAR")
    def fn() -> None:
        pass

    with pytest.raises(OSError, match="MISSING_VAR"):
        fn()


def test_validate_env_raises_for_multiple_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("VAR_A", raising=False)
    monkeypatch.delenv("VAR_B", raising=False)

    @validate_env("VAR_A", "VAR_B")
    def fn() -> None:
        pass

    with pytest.raises(OSError) as exc_info:
        fn()

    assert "VAR_A" in str(exc_info.value)
    assert "VAR_B" in str(exc_info.value)


def test_validate_env_passes_when_all_set(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("VAR_A", "a")
    monkeypatch.setenv("VAR_B", "b")

    @validate_env("VAR_A", "VAR_B")
    def fn() -> str:
        return "ok"

    assert fn() == "ok"
