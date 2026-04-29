"""F24 — Tests des chemins de validation et des fonctions de lecture.

Utilise un mock minimal de ``Session`` pour exercer ``list_rapports`` /
``get_rapport`` sans DB, et vérifie les early-fails de ``generate_rapport``.
"""

from __future__ import annotations

import uuid
from typing import Any
from unittest.mock import MagicMock

import pytest

from app.rapports.service import (
    generate_rapport,
    get_rapport,
    list_rapports,
)


class _StubRow:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class _StubResult:
    def __init__(self, rows: list[_StubRow]) -> None:
        self._rows = rows

    def fetchall(self) -> list[_StubRow]:
        return self._rows

    def first(self) -> _StubRow | None:
        return self._rows[0] if self._rows else None


class _StubSession:
    def __init__(self, rows: list[_StubRow]) -> None:
        self._rows = rows
        self.last_sql: str | None = None
        self.last_params: dict | None = None

    def execute(self, stmt, params=None):  # type: ignore[no-untyped-def]
        try:
            self.last_sql = str(stmt)
        except Exception:
            self.last_sql = None
        self.last_params = params
        return _StubResult(self._rows)


class TestGenerateRapportValidation:
    def test_invalid_entity_type(self) -> None:
        db = MagicMock()
        with pytest.raises(ValueError, match="entity_type invalide"):
            generate_rapport(
                db,
                account_id=uuid.uuid4(),
                entity_type="offre",
                entity_id=uuid.uuid4(),
                referentiels=["ESG_MEFALI"],
            )

    def test_empty_referentiels(self) -> None:
        db = MagicMock()
        with pytest.raises(ValueError, match="référentiel"):
            generate_rapport(
                db,
                account_id=uuid.uuid4(),
                entity_type="entreprise",
                entity_id=uuid.uuid4(),
                referentiels=[],
            )


class TestListRapports:
    def test_returns_mapped_rows(self) -> None:
        rid = uuid.uuid4()
        eid = uuid.uuid4()
        rows = [
            _StubRow(
                id=rid,
                entity_type="entreprise",
                entity_id=eid,
                referentiels=["ESG_MEFALI"],
                language="fr",
                file_size_bytes=1234,
                generated_at="2026-04-29T10:00:00+00:00",
            )
        ]
        db = _StubSession(rows)
        out = list_rapports(db, account_id=uuid.uuid4())  # type: ignore[arg-type]
        assert len(out) == 1
        assert out[0]["rapport_id"] == rid
        assert out[0]["referentiels"] == ["ESG_MEFALI"]

    def test_filters_in_sql(self) -> None:
        eid = uuid.uuid4()
        db = _StubSession([])
        list_rapports(  # type: ignore[arg-type]
            db,
            account_id=uuid.uuid4(),
            entity_type="entreprise",
            entity_id=eid,
            limit=10,
        )
        assert db.last_sql is not None
        assert "entity_type = :etype" in db.last_sql
        assert "entity_id" in db.last_sql

    def test_empty_result(self) -> None:
        db = _StubSession([])
        out = list_rapports(db, account_id=uuid.uuid4())  # type: ignore[arg-type]
        assert out == []


class TestGetRapport:
    def test_returns_dict(self) -> None:
        rid = uuid.uuid4()
        eid = uuid.uuid4()
        rows = [
            _StubRow(
                id=rid,
                entity_type="entreprise",
                entity_id=eid,
                referentiels=["ESG_MEFALI"],
                language="fr",
                file_path="/tmp/x.pdf",
                file_size_bytes=42,
                generated_at="2026-04-29T10:00:00+00:00",
                score_snapshot_json={"sections": []},
            )
        ]
        db = _StubSession(rows)
        out = get_rapport(  # type: ignore[arg-type]
            db, account_id=uuid.uuid4(), rapport_id=rid
        )
        assert out is not None
        assert out["rapport_id"] == rid
        assert out["file_path"] == "/tmp/x.pdf"
        assert out["score_snapshot"] == {"sections": []}

    def test_returns_none_when_missing(self) -> None:
        db = _StubSession([])
        out = get_rapport(  # type: ignore[arg-type]
            db, account_id=uuid.uuid4(), rapport_id=uuid.uuid4()
        )
        assert out is None
