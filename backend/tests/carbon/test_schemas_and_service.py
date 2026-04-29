"""F28 - Tests schemas Pydantic + service via FakeSession (sans DB)."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.carbon import service as carbon_service
from app.carbon.engine import FactorRef
from app.carbon.schemas import CarbonComputeRequest, CarbonSourceItem

# ---------- Schemas ----------


def test_compute_request_valid():
    req = CarbonComputeRequest(
        year=2024,
        source_data=[CarbonSourceItem(code="ELEC", quantity=Decimal("100"))],
    )
    assert req.year == 2024
    assert len(req.source_data) == 1


def test_compute_request_year_out_of_range():
    with pytest.raises(ValidationError):
        CarbonComputeRequest(
            year=1900, source_data=[CarbonSourceItem(code="X", quantity=1)]
        )


def test_compute_request_empty_source_data():
    with pytest.raises(ValidationError):
        CarbonComputeRequest(year=2024, source_data=[])


def test_source_item_negative_quantity():
    with pytest.raises(ValidationError):
        CarbonSourceItem(code="ELEC", quantity=Decimal("-1"))


def test_source_item_extra_forbidden():
    with pytest.raises(ValidationError):
        CarbonSourceItem(code="ELEC", quantity=1, extra="boom")  # type: ignore[call-arg]


def test_source_item_country_validates_iso2():
    item = CarbonSourceItem(code="ELEC", quantity=1, country="CI")
    assert item.country == "CI"
    with pytest.raises(ValidationError):
        CarbonSourceItem(code="ELEC", quantity=1, country="CIV")


# ---------- Service _resolve_factor (FakeSession + monkeypatch) ----------


class _FakeSession:
    pass


def test_resolve_factor_not_found(monkeypatch):
    def _none(*args, **kwargs):
        return None

    monkeypatch.setattr(
        "app.catalog.facteurs_emission.lookup.get_facteur", _none
    )
    with pytest.raises(carbon_service.FactorNotFound):
        carbon_service._resolve_factor(_FakeSession(), "MISSING", "CI", 2024)


def test_resolve_factor_returns_factorref(monkeypatch):
    fake_row = {
        "id": uuid4(),
        "code": "ELEC_CIV",
        "valeur": Decimal("0.456"),
        "unite": "kWh",
        "scope": "2",
        "categorie": "energie",
        "source_id": uuid4(),
        "version": 1,
    }

    def _row(db, code, pays_iso2=None, at=None):
        assert code == "ELEC_CIV"
        assert pays_iso2 == "CI"
        assert isinstance(at, date)
        return fake_row

    monkeypatch.setattr(
        "app.catalog.facteurs_emission.lookup.get_facteur", _row
    )
    factor = carbon_service._resolve_factor(_FakeSession(), "ELEC_CIV", "CI", 2024)
    assert isinstance(factor, FactorRef)
    assert factor.code == "ELEC_CIV"
    assert factor.valeur == Decimal("0.456")
    assert factor.scope == "2"


# ---------- Smoke imports ----------


def test_router_module_imports():
    from app.carbon.router import router

    assert router is not None
    routes = [r.path for r in router.routes]  # type: ignore[attr-defined]
    assert "/me/carbon/compute" in routes
    assert "/me/carbon/{year}" in routes
    assert "/me/carbon/{year}/reduction-plan" in routes


def test_model_imports():
    from app.models.carbon_footprint import CarbonFootprint

    assert CarbonFootprint.__tablename__ == "carbon_footprint"
