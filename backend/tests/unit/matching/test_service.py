"""F25 — Tests unitaires du service matching avec FakeSession (sans DB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

import pytest

from app.matching import service as svc
from app.matching.schemas import OfferMatch

PROJET_ID = uuid.UUID("aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa")
ACCOUNT_ID = uuid.UUID("bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb")
FONDS_ID = uuid.UUID("cccccccc-cccc-cccc-cccc-cccccccccccc")
INTER_ID = uuid.UUID("dddddddd-dddd-dddd-dddd-dddddddddddd")
OFFRE_ID = uuid.UUID("eeeeeeee-eeee-eeee-eeee-eeeeeeeeeeee")


class FakeMappings:
    def __init__(self, rows: list[dict[str, Any]] | dict[str, Any] | None) -> None:
        self._rows = rows

    def first(self) -> dict[str, Any] | None:
        if self._rows is None:
            return None
        if isinstance(self._rows, dict):
            return self._rows
        return self._rows[0] if self._rows else None

    def all(self) -> list[dict[str, Any]]:
        if self._rows is None:
            return []
        if isinstance(self._rows, dict):
            return [self._rows]
        return list(self._rows)


class FakeResult:
    def __init__(self, mappings_value: list[dict[str, Any]] | dict[str, Any] | None) -> None:
        self._m = mappings_value

    def mappings(self) -> FakeMappings:
        return FakeMappings(self._m)


class _NestedSP:
    def commit(self) -> None:
        pass

    def rollback(self) -> None:
        pass


class FakeSession:
    def __init__(self) -> None:
        self.queue: list[FakeResult] = []
        self.executed: list[tuple[str, dict[str, Any]]] = []

    def queue_results(self, *results: FakeResult) -> None:
        self.queue.extend(results)

    def execute(self, sql: Any, params: dict[str, Any] | None = None) -> FakeResult:
        self.executed.append((str(sql), params or {}))
        if not self.queue:
            return FakeResult(None)
        return self.queue.pop(0)

    def begin_nested(self) -> _NestedSP:
        return _NestedSP()


def _fake_projet(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": PROJET_ID,
        "account_id": ACCOUNT_ID,
        "montant_recherche_amount": Decimal("100000"),
        "montant_recherche_currency": "EUR",
        "types_impact": ["climat"],
        "localisation_pays_iso2": "CI",
        "structure_financement_arr": ["subvention"],
    }
    base.update(overrides)
    return base


def _fake_offre_row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "offre_id": OFFRE_ID,
        "offre_name": "Offre Test",
        "offre_deadline": datetime(2026, 12, 31, tzinfo=UTC),
        "offre_criteres": [],
        "offre_documents": [],
        "offre_frais": {},
        "offre_delais": {"instruction_jours": 90},
        "fonds_id": FONDS_ID,
        "fonds_name": "GCF",
        "fonds_thematique": ["climat"],
        "fonds_instruments": ["subvention"],
        "fonds_plafond": {"amount": "1000000", "currency": "EUR"},
        "fonds_plancher": {"amount": "10000", "currency": "EUR"},
        "fonds_geo": ["CI", "SN"],
        "fonds_criteres": [],
        "fonds_documents": ["bp.pdf", "etude_impact.pdf"],
        "fonds_frais": {"amount": "0", "currency": "EUR"},
        "fonds_delais": {"instruction_jours": 120},
        "fonds_source_ids": [],
        "intermediaire_id": INTER_ID,
        "intermediaire_name": "BOAD",
        "intermediaire_pays": ["CI", "BJ"],
        "intermediaire_criteres": [],
        "intermediaire_documents": ["statuts.pdf"],
        "intermediaire_frais": {},
        "intermediaire_delais": {"instruction_jours": 30},
        "intermediaire_source_ids": [],
    }
    base.update(overrides)
    return base


def test_match_projet_not_found_raises():
    db = FakeSession()
    db.queue_results(FakeResult(None))
    with pytest.raises(svc.ProjetNotFound):
        svc.match(db, account_id=ACCOUNT_ID, projet_id=PROJET_ID)


def test_match_returns_sorted_offer_matches():
    db = FakeSession()
    db.queue_results(FakeResult(_fake_projet()))
    db.queue_results(
        FakeResult(
            [
                _fake_offre_row(),
                _fake_offre_row(
                    offre_id=uuid.uuid4(),
                    fonds_geo=["FR"],
                    offre_name="Offre Mauvaise",
                ),
            ]
        )
    )
    items = svc.match(db, account_id=ACCOUNT_ID, projet_id=PROJET_ID)
    assert len(items) == 2
    assert isinstance(items[0], OfferMatch)
    assert items[0].score_global > 0
    assert items[1].score_global == 0


def test_match_blocking_money_zero_score():
    db = FakeSession()
    db.queue_results(FakeResult(_fake_projet(montant_recherche_amount=Decimal("99999999"))))
    db.queue_results(FakeResult([_fake_offre_row()]))
    items = svc.match(db, account_id=ACCOUNT_ID, projet_id=PROJET_ID)
    assert items[0].fonds_score == 0.0


def test_match_min_global_is_min_of_two():
    db = FakeSession()
    db.queue_results(FakeResult(_fake_projet(localisation_pays_iso2="BJ")))
    db.queue_results(FakeResult([_fake_offre_row()]))
    items = svc.match(db, account_id=ACCOUNT_ID, projet_id=PROJET_ID)
    om = items[0]
    assert om.score_global == min(om.fonds_score, om.intermediaire_score)


def test_detail_offre_not_found_raises():
    db = FakeSession()
    db.queue_results(FakeResult(_fake_projet()))
    db.queue_results(FakeResult([]))
    with pytest.raises(svc.OffreNotFound):
        svc.detail(db, account_id=ACCOUNT_ID, projet_id=PROJET_ID, offre_id=OFFRE_ID)


def test_detail_returns_full_match():
    db = FakeSession()
    db.queue_results(FakeResult(_fake_projet()))
    db.queue_results(FakeResult([_fake_offre_row()]))
    md = svc.detail(db, account_id=ACCOUNT_ID, projet_id=PROJET_ID, offre_id=OFFRE_ID)
    assert md.offre_id == OFFRE_ID
    assert md.score_global == min(md.fonds_score, md.intermediaire_score)
    assert "bp.pdf" in md.documents_requis
    assert "statuts.pdf" in md.documents_requis
    assert md.delais_effectifs_jours == 90


def test_comparator_sorts_and_limits():
    db = FakeSession()
    db.queue_results(FakeResult(_fake_projet()))
    rows = [
        _fake_offre_row(offre_id=uuid.uuid4(), intermediaire_name="UNDP", fonds_geo=["FR"]),
        _fake_offre_row(offre_id=uuid.uuid4(), intermediaire_name="BOAD"),
        _fake_offre_row(offre_id=uuid.uuid4(), intermediaire_name="Acumen"),
    ]
    db.queue_results(FakeResult(rows))
    out = svc.comparator(
        db,
        account_id=ACCOUNT_ID,
        fonds_id=FONDS_ID,
        projet_id=PROJET_ID,
        limit=2,
    )
    assert len(out) == 2
    assert out[0].score_global >= out[1].score_global


def test_comparator_projet_not_found():
    db = FakeSession()
    db.queue_results(FakeResult(None))
    with pytest.raises(svc.ProjetNotFound):
        svc.comparator(db, account_id=ACCOUNT_ID, fonds_id=FONDS_ID, projet_id=PROJET_ID)


def test_serialize_offer_match_round_trip():
    om = OfferMatch(
        offre_id=OFFRE_ID,
        fonds_id=FONDS_ID,
        intermediaire_id=INTER_ID,
        fonds_score=80.0,
        intermediaire_score=70.0,
        score_global=70.0,
        libelle="X",
        deadline_iso="2026-12-31T00:00:00+00:00",
    )
    d = svc.serialize_offer_match(om)
    assert d["offre_id"] == str(OFFRE_ID)
    assert d["score_global"] == 70.0


def test_safe_money_handles_invalid():
    assert svc._safe_money(None) is None
    assert svc._safe_money({"amount": None, "currency": "EUR"}) is None
    m = svc._safe_money({"amount": "100", "currency": "EUR"})
    assert m is not None
    assert m.amount == Decimal("100")


def test_safe_int_handles_keys():
    assert svc._safe_int({"instruction_jours": 30}, "instruction_jours") == 30
    assert svc._safe_int({"x": "abc"}, "x") is None
    assert svc._safe_int(None, "x") is None


def test_merge_documents_dedup():
    docs = svc._merge_documents(
        ["a.pdf", {"label": "b.pdf"}],
        ["b.pdf", {"name": "c.pdf"}],
        [{"code": "d"}],
    )
    assert docs == ["a.pdf", "b.pdf", "c.pdf", "d"]
