"""F06 T057 — Unit tests for pagination cursor helpers."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from fastapi import HTTPException

from app.admin.pagination import build_page, decode_cursor, encode_cursor


def test_encode_decode_roundtrip():
    ts = datetime(2026, 4, 29, 10, 30, tzinfo=UTC)
    cursor = encode_cursor(ts, "abc-123")
    decoded = decode_cursor(cursor)
    assert decoded["id"] == "abc-123"
    assert decoded["created_at"] == ts


def test_decode_none_returns_none():
    assert decode_cursor(None) is None
    assert decode_cursor("") is None


def test_decode_garbage_raises_400():
    with pytest.raises(HTTPException) as exc:
        decode_cursor("not-base64-!!!")
    assert exc.value.status_code == 400


def test_build_page_no_more():
    items = [{"id": str(i), "created_at": datetime.now(tz=UTC)} for i in range(3)]
    page = build_page(items, limit=10, total_estimate=3)
    assert len(page["items"]) == 3
    assert page["next_cursor"] is None
    assert page["total_estimate"] == 3


def test_build_page_has_more():
    items = [{"id": str(i), "created_at": datetime(2026, 4, 29, 10, i, tzinfo=UTC)} for i in range(11)]
    page = build_page(items, limit=10, total_estimate=100)
    assert len(page["items"]) == 10
    assert page["next_cursor"] is not None
