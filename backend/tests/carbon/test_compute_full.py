"""F28 - Tests compute_footprint + get_latest + reduction_plan via FakeSession."""

from __future__ import annotations

from decimal import Decimal
from uuid import UUID, uuid4

import pytest

from app.carbon import service as carbon_service
from app.carbon.schemas import CarbonComputeRequest, CarbonSourceItem


class FakeRow:
    def __init__(self, mapping: dict):
        self._mapping = mapping

    def first(self):
        return self


class _NoneResult:
    def first(self):
        return None


class FakeSession:
    """Stub Session : capture execute() pour assertions, retourne FakeRow."""

    def __init__(self, select_row: dict | None = None):
        self.executed: list[tuple[str, dict]] = []
        self._select_row = select_row

    def execute(self, stmt, params=None):
        sql = str(stmt)
        self.executed.append((sql, params or {}))
        if "INSERT INTO carbon_footprint" in sql:
            return self
        if "INSERT INTO audit_log" in sql:
            return self
        if "SELECT id, year, total_tco2e" in sql:
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


@pytest.fixture()
def patch_factor(monkeypatch):
    fake_factor_id = uuid4()
    fake_source_id = uuid4()

    def _row(db, code, pays_iso2=None, at=None):
        return {
            "id": fake_factor_id,
            "code": code,
            "valeur": Decimal("0.5"),
            "unite": "kWh" if "ELEC" in code else "litre",
            "scope": "2" if "ELEC" in code else "1",
            "categorie": "energie",
            "source_id": fake_source_id,
            "version": 1,
        }

    monkeypatch.setattr(
        "app.catalog.facteurs_emission.lookup.get_facteur", _row
    )
    return fake_factor_id, fake_source_id


def test_compute_footprint_happy(patch_factor):
    db = FakeSession()
    account = uuid4()
    req = CarbonComputeRequest(
        year=2024,
        source_data=[
            CarbonSourceItem(code="ELEC_CIV", quantity=Decimal("100"), country="CI"),
            CarbonSourceItem(code="DIESEL", quantity=Decimal("50")),
        ],
    )
    result = carbon_service.compute_footprint(
        db,
        account_id=account,
        entreprise_id=None,
        user_id=None,
        request=req,
    )
    assert result["total_tco2e"] == Decimal("0.075000")
    assert isinstance(result["id"], UUID)
    assert len(result["breakdown"]) == 2
    assert result["breakdown"][0]["factor_id"]
    assert result["breakdown"][0]["factor_source_id"]
    sqls = [s for s, _ in db.executed]
    assert any("INSERT INTO carbon_footprint" in s for s in sqls)


def test_compute_footprint_factor_missing(monkeypatch):
    monkeypatch.setattr(
        "app.catalog.facteurs_emission.lookup.get_facteur", lambda *a, **k: None
    )
    db = FakeSession()
    req = CarbonComputeRequest(
        year=2024,
        source_data=[CarbonSourceItem(code="UNKNOWN", quantity=Decimal("1"))],
    )
    with pytest.raises(carbon_service.FactorNotFound):
        carbon_service.compute_footprint(
            db, account_id=uuid4(), entreprise_id=None, user_id=None, request=req
        )


def test_get_latest_not_found():
    db = FakeSession(select_row=None)
    with pytest.raises(carbon_service.FootprintNotFound):
        carbon_service.get_latest(db, account_id=uuid4(), year=2024)


def test_get_latest_returns_aggregated():
    fp_id = uuid4()
    db = FakeSession(
        select_row={
            "id": fp_id,
            "year": 2024,
            "total_tco2e": Decimal("0.123456"),
            "by_scope_json": {"1": "10", "2": "100", "3": "0"},
            "breakdown_json": [
                {"code": "ELEC", "categorie": "energie", "kgco2e": "60"},
                {"code": "TRI", "categorie": "dechets", "kgco2e": "50"},
            ],
            "factor_versions_json": [{"code": "ELEC"}],
        }
    )
    result = carbon_service.get_latest(db, account_id=uuid4(), year=2024)
    assert result["id"] == fp_id
    assert result["total_tco2e"] == Decimal("0.123456")
    assert result["by_scope_kgco2e"]["2"] == Decimal("100")
    assert result["by_category_kgco2e"]["energie"] == Decimal("60")
    assert result["by_category_kgco2e"]["dechets"] == Decimal("50")


def test_reduction_plan_uses_latest():
    db = FakeSession(
        select_row={
            "id": uuid4(),
            "year": 2024,
            "total_tco2e": Decimal("1"),
            "by_scope_json": {"1": "0", "2": "100", "3": "0"},
            "breakdown_json": [
                {"code": "ELEC", "categorie": "energie", "kgco2e": "100"}
            ],
            "factor_versions_json": [],
        }
    )
    result = carbon_service.reduction_plan(db, account_id=uuid4(), year=2024)
    assert result["year"] == 2024
    assert len(result["actions"]) >= 1
    assert all(a["category"] == "energie" for a in result["actions"])
    assert all(isinstance(a["impact_kgco2e_year"], str) for a in result["actions"])
