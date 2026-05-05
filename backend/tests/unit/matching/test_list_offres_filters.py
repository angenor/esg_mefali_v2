"""F51 T017/T018 — Tests unitaires pour list_offres_for_account / get_offre_detail."""

from __future__ import annotations

import uuid
from decimal import Decimal
from typing import Any

import pytest

from app.matching import service as svc

ACCOUNT_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
FONDS_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
INTER_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
OFFRE_ID_1 = uuid.UUID("11111111-1111-1111-1111-111111111111")
OFFRE_ID_2 = uuid.UUID("22222222-2222-2222-2222-222222222222")


class FakeResult:
    def __init__(self, rows: list[dict[str, Any]] | dict[str, Any] | None) -> None:
        self._rows = rows

    def mappings(self) -> FakeResult:
        return self

    def all(self) -> list[dict[str, Any]]:
        if self._rows is None:
            return []
        if isinstance(self._rows, dict):
            return [self._rows]
        return list(self._rows)

    def first(self) -> dict[str, Any] | None:
        rows = self.all()
        return rows[0] if rows else None


class FakeSession:
    def __init__(self, queue: list[FakeResult]) -> None:
        self.queue = list(queue)
        self.executed_params: list[dict[str, Any]] = []

    def execute(self, _sql: Any, params: dict[str, Any] | None = None) -> FakeResult:
        self.executed_params.append(params or {})
        if not self.queue:
            return FakeResult(None)
        return self.queue.pop(0)


def _row(
    *,
    offre_id: uuid.UUID = OFFRE_ID_1,
    offre_type: str | None = None,
    fonds_type: str | None = "credit",
    plafond: tuple[Decimal, str] | None = (Decimal("500000"), "EUR"),
    plancher: tuple[Decimal, str] | None = (Decimal("10000"), "EUR"),
    duree_min: int | None = 12,
    duree_max: int | None = 84,
    secteurs: list[str] | None = None,
    intermediaire_id: uuid.UUID | None = INTER_ID,
    geo: tuple[float, float] | None = (5.31, -4.04),
    accepted_languages: list[str] | None = None,
) -> dict[str, Any]:
    return {
        "offre_id": offre_id,
        "offre_name": "Ligne verte BICC 2024",
        "offre_type": offre_type,
        "duree_min_mois": duree_min,
        "duree_max_mois": duree_max,
        "accepted_languages": accepted_languages or ["fr"],
        "fonds_id": FONDS_ID,
        "fonds_name": "GCF Climat",
        "fonds_type": fonds_type,
        "fonds_thematique": "climat",
        "secteurs": secteurs or ["renouvelable"],
        "plafond_amount": plafond[0] if plafond else None,
        "plafond_currency": plafond[1] if plafond else None,
        "plancher_amount": plancher[0] if plancher else None,
        "plancher_currency": plancher[1] if plancher else None,
        "intermediaire_id": intermediaire_id,
        "intermediaire_name": "BICC",
        "geo_lat": geo[0] if geo else None,
        "geo_lng": geo[1] if geo else None,
    }


@pytest.mark.unit
def test_list_offres_returns_normalized_items() -> None:
    s = FakeSession([FakeResult([_row()])])
    items = svc.list_offres_for_account(
        s, account_id=ACCOUNT_ID, filters={}, limit=20
    )
    assert len(items) == 1
    it = items[0]
    assert it["nom"] == "Ligne verte BICC 2024"
    assert it["type"] == "credit"  # mapping fonds_type → OffreType
    assert it["intermediaire"]["nom"] == "BICC"
    assert it["intermediaire"]["geolocation"] == {"lat": 5.31, "lng": -4.04}
    assert it["montant_min"] == {"amount": "10000", "currency": "EUR"}
    assert it["montant_max"] == {"amount": "500000", "currency": "EUR"}
    assert it["duree_min_mois"] == 12
    assert it["secteurs"] == ["renouvelable"]


@pytest.mark.unit
def test_list_offres_maps_subvention_from_grant() -> None:
    s = FakeSession([FakeResult([_row(fonds_type="grant")])])
    items = svc.list_offres_for_account(s, account_id=ACCOUNT_ID, filters={}, limit=20)
    assert items[0]["type"] == "subvention"


@pytest.mark.unit
def test_list_offres_offre_type_overrides_fonds_type() -> None:
    s = FakeSession([FakeResult([_row(offre_type="garantie", fonds_type="credit")])])
    items = svc.list_offres_for_account(s, account_id=ACCOUNT_ID, filters={}, limit=20)
    assert items[0]["type"] == "garantie"


@pytest.mark.unit
def test_list_offres_unknown_type_falls_back_to_autre() -> None:
    s = FakeSession([FakeResult([_row(fonds_type="something-exotic")])])
    items = svc.list_offres_for_account(s, account_id=ACCOUNT_ID, filters={}, limit=20)
    assert items[0]["type"] == "autre"


@pytest.mark.unit
def test_list_offres_filters_by_montant_max_eur_post_query() -> None:
    """Une offre dont le plancher = 100k EUR doit être exclue par montant_max=50k."""
    rows = [
        _row(offre_id=OFFRE_ID_1, plancher=(Decimal("100000"), "EUR")),
        _row(offre_id=OFFRE_ID_2, plancher=(Decimal("10000"), "EUR")),
    ]
    s = FakeSession([FakeResult(rows)])
    items = svc.list_offres_for_account(
        s, account_id=ACCOUNT_ID, filters={"montant_max_eur": 50000}, limit=20
    )
    assert len(items) == 1
    assert items[0]["offre_id"] == str(OFFRE_ID_2)


@pytest.mark.unit
def test_list_offres_filters_by_montant_min_eur_post_query() -> None:
    """Une offre dont le plafond = 5k EUR doit être exclue par montant_min=10k."""
    rows = [
        _row(offre_id=OFFRE_ID_1, plafond=(Decimal("5000"), "EUR"), plancher=(Decimal("1000"), "EUR")),
        _row(offre_id=OFFRE_ID_2, plafond=(Decimal("500000"), "EUR")),
    ]
    s = FakeSession([FakeResult(rows)])
    items = svc.list_offres_for_account(
        s, account_id=ACCOUNT_ID, filters={"montant_min_eur": 10000}, limit=20
    )
    assert len(items) == 1
    assert items[0]["offre_id"] == str(OFFRE_ID_2)


@pytest.mark.unit
def test_list_offres_xof_montant_converted_to_eur_for_filter() -> None:
    """6.55M XOF ≈ 10k EUR — devrait être inclus avec montant_max_eur=20k."""
    rows = [
        _row(
            offre_id=OFFRE_ID_1,
            plafond=(Decimal("6559570"), "XOF"),
            plancher=(Decimal("655957"), "XOF"),
        ),
    ]
    s = FakeSession([FakeResult(rows)])
    items = svc.list_offres_for_account(
        s, account_id=ACCOUNT_ID, filters={"montant_max_eur": 20000}, limit=20
    )
    assert len(items) == 1
    assert items[0]["montant_max"]["currency"] == "XOF"


@pytest.mark.unit
def test_list_offres_no_geolocation_when_lat_lng_null() -> None:
    s = FakeSession([FakeResult([_row(geo=None)])])
    items = svc.list_offres_for_account(s, account_id=ACCOUNT_ID, filters={}, limit=20)
    assert items[0]["intermediaire"]["geolocation"] is None


@pytest.mark.unit
def test_get_offre_detail_returns_none_if_not_found() -> None:
    s = FakeSession([FakeResult(None)])
    out = svc.get_offre_detail(s, account_id=ACCOUNT_ID, offre_id=OFFRE_ID_1)
    assert out is None


@pytest.mark.unit
def test_get_offre_detail_aggregates_documents_requis() -> None:
    row = _row()
    row["criteres_offre"] = []
    row["documents_offre"] = [{"key": "k_kbis", "label": "Kbis", "format": "pdf"}]
    row["fonds_documents"] = [{"key": "k_business_plan", "label": "Plan d'affaires"}]
    row["intermediaire_documents"] = ["États financiers 2 ans"]
    s = FakeSession([FakeResult(row)])
    out = svc.get_offre_detail(s, account_id=ACCOUNT_ID, offre_id=OFFRE_ID_1)
    assert out is not None
    keys = {d["key"] for d in out["documents_requis"]}
    assert "k_kbis" in keys
    assert "k_business_plan" in keys
    # Le doc fourni en string a été normalisé en clé snake_case lowercase.
    assert any("etats" in k or "états" in k for k in keys) or any(
        "financiers" in d["label"].lower() for d in out["documents_requis"]
    )
