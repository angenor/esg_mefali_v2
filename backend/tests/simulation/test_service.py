"""F27 - Tests du service de simulation (sans DB, via _build_result + FakeSession)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.core.currencies import Currency
from app.simulation.schemas import SimulationHypotheses
from app.simulation.service import (
    OffreNotFound,
    ProjetNotFound,
    _build_result,
    _normalize_instrument,
    compare,
    simulate,
)

PROJET_ID = uuid4()
OFFRE_ID = uuid4()
SRC_FONDS = uuid4()
SRC_INTER = uuid4()


def make_projet(amount=Decimal("5000000"), currency="EUR", duree=84):
    return {
        "id": PROJET_ID,
        "account_id": uuid4(),
        "montant_recherche_amount": amount,
        "montant_recherche_currency": currency,
        "duree_mois": duree,
    }


def make_offre(
    instruments=None,
    plafond=None,
    offre_frais=None,
    fonds_frais=None,
    inter_frais=None,
    intermediaire_id=None,
    source_ids_fonds=None,
):
    return {
        "offre_id": OFFRE_ID,
        "offre_frais": offre_frais or {},
        "offre_source_ids": [],
        "fonds_id": uuid4(),
        "fonds_instruments": instruments or ["pret_concessionnel"],
        "fonds_plafond": plafond,
        "fonds_plancher": None,
        "fonds_frais": fonds_frais or {},
        "fonds_source_ids": [SRC_FONDS] if source_ids_fonds is None else source_ids_fonds,
        "intermediaire_id": intermediaire_id,
        "intermediaire_frais": inter_frais or {},
        "intermediaire_source_ids": [SRC_INTER] if intermediaire_id else [],
    }


def test_normalize_instrument_subvention():
    assert _normalize_instrument(["Subvention"]) == "subvention"
    assert _normalize_instrument(["grant"]) == "subvention"


def test_normalize_instrument_pret():
    assert _normalize_instrument(["pret_concessionnel"]) == "pret"
    assert _normalize_instrument(["loan"]) == "pret"


def test_normalize_instrument_equity():
    assert _normalize_instrument(["equity"]) == "equity"


def test_normalize_instrument_blending():
    assert _normalize_instrument(["blending"]) == "blending"


def test_normalize_instrument_unknown():
    assert _normalize_instrument([]) == "unknown"
    assert _normalize_instrument(None) == "unknown"
    assert _normalize_instrument(["xyz"]) == "unknown"


def test_pret_simple_eur_5m_7ans():
    """Spec SC-001 : projet 5M EUR + Offre pret 2% marge + 1% frais + 30% garantie + 4% sur 7 ans."""
    projet = make_projet()
    offre = make_offre(
        instruments=["pret_concessionnel"],
        intermediaire_id=uuid4(),
        offre_frais={"frais_dossier_pct": "1.0", "garantie_pct": "30"},
        fonds_frais={"taux_interet_pct": "4.0"},
        inter_frais={"marge_pct": "2.0"},
    )
    result = _build_result(projet=projet, offre=offre, hypotheses=None)

    assert result.instrument == "pret"
    assert result.montant_eligible.amount == Decimal("5000000")
    assert result.montant_eligible.currency == Currency.EUR
    assert result.marge_intermediaire is not None
    assert result.marge_intermediaire.amount == Decimal("100000.00")
    assert result.frais_dossier is not None
    assert result.frais_dossier.amount == Decimal("50000.00")
    assert result.garantie_exigee is not None
    assert result.garantie_exigee.amount == Decimal("1500000.00")
    assert result.interets_cumules is not None
    assert result.interets_cumules.amount == Decimal("1400000.00")
    assert result.cout_total.amount == Decimal("1550000.00")
    assert result.cout_total_pct == Decimal("31.00")
    assert result.equivalent_xof is not None
    assert result.equivalent_xof.currency == Currency.XOF
    assert result.change_risk is False
    assert result.dilution_warning is False
    assert len(result.source_ids) >= 1
    assert result.unsourced is False


def test_subvention_cout_total_zero():
    projet = make_projet()
    offre = make_offre(instruments=["subvention"])
    result = _build_result(projet=projet, offre=offre, hypotheses=None)

    assert result.instrument == "subvention"
    assert result.cout_total.amount == Decimal("0.00")
    assert result.taux_interet_pct == Decimal("0")
    assert result.interets_cumules is not None
    assert result.interets_cumules.amount == Decimal("0.00")


def test_equity_dilution_warning():
    projet = make_projet()
    offre = make_offre(instruments=["equity"])
    result = _build_result(projet=projet, offre=offre, hypotheses=None)

    assert result.instrument == "equity"
    assert result.dilution_warning is True
    assert result.taux_interet_pct == Decimal("0")


def test_change_risk_usd():
    projet = make_projet(currency="USD")
    offre = make_offre(instruments=["pret_concessionnel"])
    result = _build_result(projet=projet, offre=offre, hypotheses=None)

    assert result.change_risk is True
    assert result.equivalent_xof is None
    assert "fx_rate" in result.unknown_fields


def test_xof_no_change_risk():
    projet = make_projet(currency="XOF", amount=Decimal("3279785000"))
    offre = make_offre(instruments=["pret_concessionnel"])
    result = _build_result(projet=projet, offre=offre, hypotheses=None)

    assert result.change_risk is False
    assert result.equivalent_xof is not None
    assert result.devise_emprunt == Currency.XOF


def test_unknown_fields_when_missing_data():
    projet = make_projet()
    offre = make_offre(
        instruments=["pret_concessionnel"],
        intermediaire_id=uuid4(),
        offre_frais={},
        fonds_frais={},
        inter_frais={},
    )
    result = _build_result(projet=projet, offre=offre, hypotheses=None)

    assert "taux_interet_pct" in result.unknown_fields
    assert "marge_intermediaire" in result.unknown_fields
    assert "frais_dossier" in result.unknown_fields
    assert len(result.notes) >= 1


def test_unsourced_when_no_source_ids():
    projet = make_projet()
    offre = make_offre(
        instruments=["subvention"],
        source_ids_fonds=[],
    )
    result = _build_result(projet=projet, offre=offre, hypotheses=None)
    assert result.unsourced is True
    assert result.source_ids == []


def test_hypotheses_override_taux():
    projet = make_projet()
    offre = make_offre(instruments=["pret_concessionnel"])
    h = SimulationHypotheses(taux_interet_pct=Decimal("2"), duree_mois=60)
    result = _build_result(projet=projet, offre=offre, hypotheses=h)

    assert result.taux_interet_pct == Decimal("2")
    assert result.duree_mois == 60
    assert result.interets_cumules is not None
    assert result.interets_cumules.amount == Decimal("500000.00")


def test_plafond_clipping():
    projet = make_projet(amount=Decimal("10000000"))
    offre = make_offre(
        instruments=["pret_concessionnel"],
        plafond={"amount": "5000000", "currency": "EUR"},
    )
    result = _build_result(projet=projet, offre=offre, hypotheses=None)

    assert result.montant_eligible.amount == Decimal("5000000")


def test_duree_unknown_when_missing():
    projet = make_projet(duree=None)
    offre = make_offre(instruments=["pret_concessionnel"])
    result = _build_result(projet=projet, offre=offre, hypotheses=None)

    assert result.duree_mois is None
    assert result.interets_cumules is None
    assert "duree_mois" in result.unknown_fields


def test_compare_too_few_offres_raises():
    class FakeDb:
        pass

    with pytest.raises(ValueError):
        compare(
            FakeDb(),  # type: ignore[arg-type]
            account_id=uuid4(),
            projet_id=uuid4(),
            offre_ids=[uuid4()],
        )


def test_compare_too_many_offres_raises():
    class FakeDb:
        pass

    with pytest.raises(ValueError):
        compare(
            FakeDb(),  # type: ignore[arg-type]
            account_id=uuid4(),
            projet_id=uuid4(),
            offre_ids=[uuid4() for _ in range(6)],
        )


def test_compare_duplicates_raise():
    class FakeDb:
        pass

    same = uuid4()
    with pytest.raises(ValueError):
        compare(
            FakeDb(),  # type: ignore[arg-type]
            account_id=uuid4(),
            projet_id=uuid4(),
            offre_ids=[same, same],
        )


class FakeSession:
    """Mock minimal de Session pour tester simulate sans DB."""

    def __init__(self, projet_row=None, offre_rows=None):
        self.projet_row = projet_row
        self.offre_rows = offre_rows or {}

    def execute(self, stmt, params):
        sql = str(stmt)
        if "FROM projet" in sql:
            return _FakeResult(self.projet_row)
        if "FROM offre" in sql:
            row = self.offre_rows.get(params.get("oid"))
            return _FakeResult(row)
        return _FakeResult(None)


class _FakeResult:
    def __init__(self, row):
        self.row = row

    def mappings(self):
        return self

    def first(self):
        return self.row


def test_simulate_projet_not_found():
    sess = FakeSession(projet_row=None)
    with pytest.raises(ProjetNotFound):
        simulate(
            sess,  # type: ignore[arg-type]
            account_id=uuid4(),
            projet_id=PROJET_ID,
            offre_id=OFFRE_ID,
        )


def test_simulate_offre_not_found():
    sess = FakeSession(projet_row=make_projet(), offre_rows={})
    with pytest.raises(OffreNotFound):
        simulate(
            sess,  # type: ignore[arg-type]
            account_id=uuid4(),
            projet_id=PROJET_ID,
            offre_id=OFFRE_ID,
        )


def test_simulate_happy_path():
    offre = make_offre(instruments=["subvention"])
    sess = FakeSession(
        projet_row=make_projet(),
        offre_rows={str(OFFRE_ID): offre},
    )
    result = simulate(
        sess,  # type: ignore[arg-type]
        account_id=uuid4(),
        projet_id=PROJET_ID,
        offre_id=OFFRE_ID,
    )
    assert result.instrument == "subvention"
    assert result.cout_total.amount == Decimal("0.00")


def test_compare_sorts_by_cout_total_asc():
    o1, o2 = uuid4(), uuid4()
    offre1 = make_offre(
        instruments=["pret_concessionnel"],
        intermediaire_id=uuid4(),
        offre_frais={"frais_dossier_pct": "5"},
        fonds_frais={"taux_interet_pct": "5"},
        inter_frais={"marge_pct": "5"},
    )
    offre1["offre_id"] = o1
    offre2 = make_offre(instruments=["subvention"])
    offre2["offre_id"] = o2

    sess = FakeSession(
        projet_row=make_projet(),
        offre_rows={str(o1): offre1, str(o2): offre2},
    )
    result = compare(
        sess,  # type: ignore[arg-type]
        account_id=uuid4(),
        projet_id=PROJET_ID,
        offre_ids=[o1, o2],
    )
    assert len(result.rows) == 2
    assert result.rows[0].instrument == "subvention"
    assert result.rows[1].instrument == "pret"
