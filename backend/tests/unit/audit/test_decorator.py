"""F04 — Unit tests for ``@journal_llm_mutation`` (T050, US2)."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import UUID, uuid4

import pytest
from sqlalchemy.orm import Session

from app.audit.decorator import journal_llm_mutation
from app.audit.schemas import SourceOfChange


class _StubResult:
    def __init__(self, oid: UUID) -> None:
        self.id = oid


@pytest.mark.asyncio
async def test_async_decorator_calls_record_audit(monkeypatch) -> None:
    captured: dict[str, Any] = {}

    def fake_record_audit(db, **kwargs):
        captured.update(kwargs)
        captured["db"] = db

    monkeypatch.setattr("app.audit.decorator.record_audit", fake_record_audit)

    db = MagicMock(spec=Session)
    target_id = uuid4()

    @journal_llm_mutation("projet", field="nom")
    async def update_projet(db: Session, **kw):
        return _StubResult(target_id)

    out = await update_projet(db, _new="Acme")
    assert out.id == target_id
    assert captured["entity_type"] == "projet"
    assert captured["entity_id"] == target_id
    assert captured["source_of_change"] == SourceOfChange.LLM
    assert captured["field"] == "nom"


def test_sync_decorator_calls_record_audit(monkeypatch) -> None:
    captured: dict[str, Any] = {}
    monkeypatch.setattr(
        "app.audit.decorator.record_audit",
        lambda db, **kw: captured.update(kw),
    )
    db = MagicMock(spec=Session)
    target_id = uuid4()

    @journal_llm_mutation("indicateur")
    def insert_indic(db: Session, **kw):
        return {"id": str(target_id)}

    insert_indic(db)
    assert UUID(str(captured["entity_id"])) == target_id
    assert captured["source_of_change"] == SourceOfChange.LLM


def test_decorator_skips_when_no_session(monkeypatch) -> None:
    called: list[bool] = []
    monkeypatch.setattr(
        "app.audit.decorator.record_audit",
        lambda *a, **kw: called.append(True),
    )

    @journal_llm_mutation("projet")
    def noop():
        return _StubResult(uuid4())

    noop()
    assert called == []  # no DB session in args -> emit skipped


def test_decorator_skips_when_no_id(monkeypatch) -> None:
    called: list[bool] = []
    monkeypatch.setattr(
        "app.audit.decorator.record_audit",
        lambda *a, **kw: called.append(True),
    )
    db = MagicMock(spec=Session)

    @journal_llm_mutation("projet")
    def noop(db):
        return None

    noop(db)
    assert called == []
