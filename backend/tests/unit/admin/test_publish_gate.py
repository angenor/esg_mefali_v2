"""F06 T027 — pure unit on verify_sources_or_422 (mocked DB)."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import HTTPException

from app.admin.publish import verify_sources_or_422
from app.admin.registry import EntitySpec


def _make_spec(rel):
    return EntitySpec(name="x", table="x", sources_relation=rel)


def _row(**fields):
    return SimpleNamespace(_mapping=fields)


def test_no_relation_returns_silently():
    spec = _make_spec(rel=None)
    db = MagicMock()
    # Should not raise.
    verify_sources_or_422(db, spec, {"id": "abc"})
    db.execute.assert_not_called()


def test_no_sources_raises_422():
    spec = _make_spec(rel=lambda r: [])
    db = MagicMock()
    with pytest.raises(HTTPException) as exc:
        verify_sources_or_422(db, spec, {"id": "abc"})
    assert exc.value.status_code == 422
    assert exc.value.detail["code"] == "sources_not_verified"
    assert exc.value.detail["missing_sources"] == []


def test_all_verified_passes():
    sid = "00000000-0000-0000-0000-000000000001"
    spec = _make_spec(rel=lambda r: [sid])
    db = MagicMock()
    db.execute.return_value.all.return_value = [
        _row(id=sid, verification_status="verified", title="OK"),
    ]
    verify_sources_or_422(db, spec, {"source_id": sid})


def test_one_pending_raises_422_with_missing():
    sid = "00000000-0000-0000-0000-000000000002"
    spec = _make_spec(rel=lambda r: [sid])
    db = MagicMock()
    db.execute.return_value.all.return_value = [
        _row(id=sid, verification_status="pending", title="Pending Source"),
    ]
    with pytest.raises(HTTPException) as exc:
        verify_sources_or_422(db, spec, {"source_id": sid})
    assert exc.value.status_code == 422
    missing = exc.value.detail["missing_sources"]
    assert len(missing) == 1
    assert missing[0]["status"] == "pending"
    assert missing[0]["label"] == "Pending Source"


def test_unknown_source_id_reported_as_unknown():
    sid = "00000000-0000-0000-0000-000000000003"
    spec = _make_spec(rel=lambda r: [sid])
    db = MagicMock()
    db.execute.return_value.all.return_value = []
    with pytest.raises(HTTPException) as exc:
        verify_sources_or_422(db, spec, {"source_id": sid})
    missing = exc.value.detail["missing_sources"]
    assert missing[0]["status"] == "unknown"
