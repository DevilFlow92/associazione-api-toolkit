"""
Pagination helpers for offset-based and cursor-based pagination.

Usage:
    from associazione_toolkit.pagination import PageParams, PagedResponse, paginate

    # In a FastAPI router:
    @router.get("/soci/")
    async def list_soci(params: PageParams = Depends()) -> PagedResponse[SocioOut]:
        items, total = await socio_service.list(offset=params.offset, limit=params.limit)
        return paginate(items, total, params)
"""

from __future__ import annotations

import base64
from typing import TypeVar

from pydantic import BaseModel, Field, model_validator

T = TypeVar("T")


class PageParams(BaseModel):
    """Query parameters for offset-based pagination.

    Inject via FastAPI Depends():
        async def endpoint(params: PageParams = Depends()) -> ...:
    """

    page: int = Field(default=1, ge=1, description="Page number (1-indexed)")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @property
    def offset(self) -> int:
        """SQL offset derived from page and page_size."""
        return (self.page - 1) * self.page_size

    @property
    def limit(self) -> int:
        """SQL limit — alias for page_size."""
        return self.page_size


class PageMeta(BaseModel):
    """Pagination metadata included in every paged response."""

    page: int
    page_size: int
    total_items: int
    total_pages: int
    has_next: bool
    has_previous: bool


class PagedResponse[T](BaseModel):
    """Generic wrapper for paginated list responses.

    Example JSON:
        {
            "items": [...],
            "meta": {
                "page": 1,
                "page_size": 20,
                "total_items": 42,
                "total_pages": 3,
                "has_next": true,
                "has_previous": false
            }
        }
    """

    items: list[T]
    meta: PageMeta


def paginate[T](items: list[T], total: int, params: PageParams) -> PagedResponse[T]:
    """
    Build a PagedResponse from a list of items, total count and page params.

    Args:
        items: The items for the current page (already sliced from DB).
        total: Total number of items across all pages.
        params: The PageParams instance from the request.

    Returns:
        A PagedResponse with items and pagination metadata.
    """
    total_pages = max(1, -(-total // params.page_size))  # ceiling division
    return PagedResponse(
        items=items,
        meta=PageMeta(
            page=params.page,
            page_size=params.page_size,
            total_items=total,
            total_pages=total_pages,
            has_next=params.page < total_pages,
            has_previous=params.page > 1,
        ),
    )


# ---------------------------------------------------------------------------
# Cursor-based pagination
# ---------------------------------------------------------------------------


class CursorParams(BaseModel):
    """Query parameters for cursor-based pagination.

    The cursor is an opaque base64-encoded string that encodes the last seen ID.
    This is more stable than offset pagination for real-time data.
    """

    cursor: str | None = Field(default=None, description="Opaque pagination cursor")
    page_size: int = Field(default=20, ge=1, le=100, description="Items per page")

    @model_validator(mode="after")
    def validate_cursor(self) -> CursorParams:
        if self.cursor is not None:
            try:
                base64.b64decode(self.cursor.encode()).decode()
            except Exception as exc:
                raise ValueError("Invalid cursor format") from exc
        return self

    @property
    def decoded_cursor(self) -> str | None:
        """Decode the cursor to its raw string value (e.g. last seen ID)."""
        if self.cursor is None:
            return None
        return base64.b64decode(self.cursor.encode()).decode()


class CursorMeta(BaseModel):
    """Metadata for cursor-based pagination responses."""

    next_cursor: str | None
    has_next: bool
    page_size: int


class CursorPagedResponse[T](BaseModel):
    """Generic wrapper for cursor-paginated list responses."""

    items: list[T]
    meta: CursorMeta


def encode_cursor(value: str) -> str:
    """Encode a raw value (e.g. last item ID) into an opaque cursor string."""
    return base64.b64encode(value.encode()).decode()


def cursor_paginate[T](
    items: list[T],
    params: CursorParams,
    next_id: str | None,
) -> CursorPagedResponse[T]:
    """
    Build a CursorPagedResponse.

    Args:
        items: The items for the current page.
        params: The CursorParams instance from the request.
        next_id: The ID of the next item after this page, or None if last page.

    Returns:
        A CursorPagedResponse with items and cursor metadata.
    """
    next_cursor = encode_cursor(next_id) if next_id is not None else None
    return CursorPagedResponse(
        items=items,
        meta=CursorMeta(
            next_cursor=next_cursor,
            has_next=next_cursor is not None,
            page_size=params.page_size,
        ),
    )
