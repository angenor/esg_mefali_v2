"""F47 — Fakes partagés pour tests carbon (FakeSession + helpers)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from uuid import UUID, uuid4


class FakeRow:
    def __init__(self, mapping: dict[str, Any]):
        self._mapping = mapping

    def first(self):
        return self


class _NoneResult:
    def first(self):
        return None

    def fetchall(self):
        return []


class FakeMultiResult:
    def __init__(self, rows: list[dict[str, Any]]):
        self._rows = rows

    def first(self):
        return FakeRow(self._rows[0]) if self._rows else None

    def fetchall(self):
        return [FakeRow(r) for r in self._rows]


class FakeSession:
    """Stub Session : capture execute() pour assertions, retourne FakeRow.

    Permet de configurer :
    - ``select_row`` : ce que renvoie le SELECT id, year, total_tco2e ... (get_latest)
    - ``select_full_row`` : idem pour _load_latest_full
    - ``index_rows`` : ce que renvoie le SELECT DISTINCT ON (year) (list_index)
    - ``source_row`` : ce que renvoie le SELECT statut FROM source (verifié)
    """

    def __init__(
        self,
        select_row: dict[str, Any] | None = None,
        select_full_row: dict[str, Any] | None = None,
        index_rows: list[dict[str, Any]] | None = None,
        source_row: dict[str, Any] | None = None,
    ):
        self.executed: list[tuple[str, dict[str, Any]]] = []
        self._select_row = select_row
        self._select_full_row = select_full_row
        self._index_rows = index_rows
        self._source_row = source_row

    def execute(self, stmt, params=None):
        sql = str(stmt)
        self.executed.append((sql, params or {}))
        if "INSERT INTO carbon_footprint" in sql:
            return self
        if "INSERT INTO audit_log" in sql:
            return self
        if "SELECT DISTINCT ON (year)" in sql:
            return FakeMultiResult(self._index_rows or [])
        if "SELECT statut FROM source" in sql:
            if self._source_row is None:
                return _NoneResult()
            return FakeRow(self._source_row)
        if "computed_at, version, source_data_json" in sql:
            # _load_latest_full
            if self._select_full_row is None:
                return _NoneResult()
            return FakeRow(self._select_full_row)
        if "SELECT id, year, total_tco2e" in sql:
            # get_latest classique
            if self._select_row is None:
                return _NoneResult()
            return FakeRow(self._select_row)
        return self

    def begin_nested(self):
        class _Ctx:
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False

            def commit(self):
                return None

            def rollback(self):
                return None

        return _Ctx()


def make_factor_lookup(scope: str = "2", categorie: str = "electricite"):
    """Retourne un (fake_factor_id, fake_source_id, callable) à monkeypatcher."""
    fake_factor_id = uuid4()
    fake_source_id = uuid4()

    def _row(db, code, pays_iso2=None, at=None):
        return {
            "id": fake_factor_id,
            "code": code,
            "valeur": Decimal("0.5"),
            "unite": "kWh",
            "scope": scope,
            "categorie": categorie,
            "source_id": fake_source_id,
            "version": 1,
        }

    return fake_factor_id, fake_source_id, _row


def fake_full_row(
    *,
    items: list[dict[str, Any]],
    version: int = 1,
    total_tco2e: str = "0.050000",
    fp_id: UUID | None = None,
) -> dict[str, Any]:
    """Construit une row de _load_latest_full avec source_data_json={items: [...]}."""
    return {
        "id": fp_id or uuid4(),
        "year": 2026,
        "total_tco2e": total_tco2e,
        "by_scope_json": {"1": "0", "2": "100", "3": "0"},
        "breakdown_json": [],
        "factor_versions_json": [],
        "computed_at": datetime.now(UTC),
        "version": version,
        "source_data_json": {"items": items},
        "entreprise_id": None,
    }
