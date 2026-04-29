"""Tests F19 — résolution des sources (sans DB, via stubs)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from app.skills.sources import EXCERPT_MAX_CHARS, resolve_sources


@dataclass
class _SourceStub:
    id: uuid.UUID
    title: str
    publisher: str
    url: str
    notes: str | None
    verification_status: str


class _QueryStub:
    def __init__(self, rows: list[_SourceStub]) -> None:
        self._rows = rows

    def filter(self, *args: Any) -> _QueryStub:  # noqa: ARG002
        return self

    def all(self) -> list[_SourceStub]:
        return [r for r in self._rows if r.verification_status == "verified"]


class _SessionStub:
    def __init__(self, rows: list[_SourceStub]) -> None:
        self._rows = rows

    def query(self, _model: Any) -> _QueryStub:  # noqa: ANN401
        return _QueryStub(self._rows)


def test_resolve_empty_returns_empty() -> None:
    assert resolve_sources([], _SessionStub([])) == []  # type: ignore[arg-type]


def test_resolve_filters_unverified() -> None:
    sid_ok = uuid.uuid4()
    sid_pending = uuid.uuid4()
    rows = [
        _SourceStub(
            id=sid_ok, title="OK", publisher="Pub", url="https://ok",
            notes="Note OK", verification_status="verified",
        ),
        _SourceStub(
            id=sid_pending, title="Pending", publisher="Pub", url="https://pending",
            notes=None, verification_status="pending",
        ),
    ]
    out = resolve_sources([sid_ok, sid_pending], _SessionStub(rows))  # type: ignore[arg-type]
    assert len(out) == 1
    assert out[0].id == sid_ok
    assert out[0].excerpt == "Note OK"


def test_resolve_truncates_long_excerpts() -> None:
    sid = uuid.uuid4()
    rows = [
        _SourceStub(
            id=sid, title="t", publisher="p", url="u",
            notes="x" * 500, verification_status="verified",
        )
    ]
    out = resolve_sources([sid], _SessionStub(rows))  # type: ignore[arg-type]
    assert len(out) == 1
    assert len(out[0].excerpt) <= EXCERPT_MAX_CHARS


def test_resolve_falls_back_to_title_when_no_notes() -> None:
    sid = uuid.uuid4()
    rows = [
        _SourceStub(
            id=sid, title="Titre court", publisher="p", url="u",
            notes=None, verification_status="verified",
        )
    ]
    out = resolve_sources([sid], _SessionStub(rows))  # type: ignore[arg-type]
    assert out[0].excerpt == "Titre court"


def test_resolve_handles_string_uuids_and_invalid() -> None:
    sid = uuid.uuid4()
    rows = [
        _SourceStub(
            id=sid, title="t", publisher="p", url="u",
            notes="n", verification_status="verified",
        )
    ]
    out = resolve_sources(
        [str(sid), "not-a-uuid"], _SessionStub(rows)  # type: ignore[arg-type]
    )
    assert len(out) == 1
    assert out[0].id == sid


def test_resolved_source_to_dict() -> None:
    sid = uuid.uuid4()
    rows = [
        _SourceStub(
            id=sid, title="t", publisher="p", url="u",
            notes="n", verification_status="verified",
        )
    ]
    out = resolve_sources([sid], _SessionStub(rows))  # type: ignore[arg-type]
    d = out[0].to_dict()
    assert d["id"] == str(sid)
    assert d["title"] == "t"
