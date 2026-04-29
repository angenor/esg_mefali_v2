"""F06 — Unit tests for ETag helpers (parse_if_match, make_etag)."""

from __future__ import annotations

import pytest
from fastapi import HTTPException

from app.admin.etag import assert_version_match, make_etag, parse_if_match


def test_make_etag_format():
    assert make_etag(1) == '"v1"'
    assert make_etag(42) == '"v42"'


def test_parse_if_match_ok():
    assert parse_if_match('"v1"') == 1
    assert parse_if_match("v1") == 1
    assert parse_if_match('"v42"') == 42


def test_parse_if_match_missing_raises_412():
    with pytest.raises(HTTPException) as exc:
        parse_if_match(None)
    assert exc.value.status_code == 412
    assert exc.value.detail["code"] == "if_match_required"


def test_parse_if_match_invalid_format_raises_412():
    with pytest.raises(HTTPException) as exc:
        parse_if_match('"abc"')
    assert exc.value.status_code == 412
    with pytest.raises(HTTPException):
        parse_if_match('"v"')


def test_assert_version_match_ok():
    assert_version_match(3, 3)  # silent


def test_assert_version_match_mismatch_raises_412():
    with pytest.raises(HTTPException) as exc:
        assert_version_match(2, 3)
    assert exc.value.status_code == 412
    assert exc.value.detail["expected"] == 2
    assert exc.value.detail["current"] == 3
