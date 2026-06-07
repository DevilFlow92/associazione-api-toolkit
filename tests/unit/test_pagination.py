"""Unit tests for associazione_toolkit.pagination."""

import pytest
from associazione_toolkit.pagination import (
    CursorParams,
    PageParams,
    cursor_paginate,
    encode_cursor,
    paginate,
)

# ---------------------------------------------------------------------------
# PageParams
# ---------------------------------------------------------------------------


def test_page_params_defaults() -> None:
    params = PageParams()
    assert params.page == 1
    assert params.page_size == 20
    assert params.offset == 0
    assert params.limit == 20


def test_page_params_offset() -> None:
    params = PageParams(page=3, page_size=10)
    assert params.offset == 20
    assert params.limit == 10


def test_page_params_invalid_page() -> None:
    with pytest.raises(ValueError):
        PageParams(page=0)


def test_page_params_invalid_page_size_too_large() -> None:
    with pytest.raises(ValueError):
        PageParams(page_size=101)


def test_page_params_invalid_page_size_zero() -> None:
    with pytest.raises(ValueError):
        PageParams(page_size=0)


# ---------------------------------------------------------------------------
# paginate()
# ---------------------------------------------------------------------------


def test_paginate_first_page() -> None:
    items = list(range(20))
    result = paginate(items, total=42, params=PageParams(page=1, page_size=20))
    assert result.meta.page == 1
    assert result.meta.total_items == 42
    assert result.meta.total_pages == 3
    assert result.meta.has_next is True
    assert result.meta.has_previous is False
    assert result.items == items


def test_paginate_last_page() -> None:
    items = list(range(2))
    result = paginate(items, total=42, params=PageParams(page=3, page_size=20))
    assert result.meta.has_next is False
    assert result.meta.has_previous is True


def test_paginate_single_page() -> None:
    items = [1, 2, 3]
    result = paginate(items, total=3, params=PageParams(page=1, page_size=20))
    assert result.meta.total_pages == 1
    assert result.meta.has_next is False
    assert result.meta.has_previous is False


def test_paginate_empty() -> None:
    result = paginate([], total=0, params=PageParams(page=1, page_size=20))
    assert result.meta.total_items == 0
    assert result.meta.total_pages == 1
    assert result.meta.has_next is False


# ---------------------------------------------------------------------------
# CursorParams
# ---------------------------------------------------------------------------


def test_cursor_params_defaults() -> None:
    params = CursorParams()
    assert params.cursor is None
    assert params.page_size == 20
    assert params.decoded_cursor is None


def test_cursor_params_encoded() -> None:
    cursor = encode_cursor("42")
    params = CursorParams(cursor=cursor)
    assert params.decoded_cursor == "42"


def test_cursor_params_invalid_cursor() -> None:
    with pytest.raises(ValueError):
        CursorParams(cursor="not-valid-base64!!!")


# ---------------------------------------------------------------------------
# cursor_paginate()
# ---------------------------------------------------------------------------


def test_cursor_paginate_has_next() -> None:
    items = list(range(20))
    result = cursor_paginate(items, params=CursorParams(page_size=20), next_id="21")
    assert result.meta.has_next is True
    assert result.meta.next_cursor is not None


def test_cursor_paginate_no_next() -> None:
    items = list(range(5))
    result = cursor_paginate(items, params=CursorParams(page_size=20), next_id=None)
    assert result.meta.has_next is False
    assert result.meta.next_cursor is None


def test_cursor_paginate_items_preserved() -> None:
    items = ["a", "b", "c"]
    result = cursor_paginate(items, params=CursorParams(), next_id=None)
    assert result.items == items
