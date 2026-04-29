"""F25 — Tests unitaires des heuristiques pures (sans DB)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.matching.heuristics import (
    LayerScore,
    eval_critere_json,
    eval_geo,
    eval_instruments,
    eval_money_range,
    eval_thematique,
    score_layer,
)
from app.matching.schemas import CritereMatch


def test_money_range_within_eur():
    c = eval_money_range(
        projet_amount=Decimal("100000"),
        projet_currency="EUR",
        plancher={"amount": "10000", "currency": "EUR"},
        plafond={"amount": "1000000", "currency": "EUR"},
    )
    assert c.covered is True
    assert c.severity == "blocking"
    assert c.reason is None


def test_money_range_above_plafond():
    c = eval_money_range(
        projet_amount=Decimal("2000000"),
        projet_currency="EUR",
        plancher=None,
        plafond={"amount": "1000000", "currency": "EUR"},
    )
    assert c.covered is False
    assert c.reason == "above_plafond"


def test_money_range_below_plancher():
    c = eval_money_range(
        projet_amount=Decimal("500"),
        projet_currency="EUR",
        plancher={"amount": "1000", "currency": "EUR"},
        plafond=None,
    )
    assert c.covered is False
    assert c.reason == "below_plancher"


def test_money_range_xof_to_eur_conversion():
    c = eval_money_range(
        projet_amount=Decimal("655957"),
        projet_currency="XOF",
        plancher={"amount": "100", "currency": "EUR"},
        plafond={"amount": "1000", "currency": "EUR"},
    )
    assert c.covered is True


def test_money_range_missing_value():
    c = eval_money_range(
        projet_amount=None,
        projet_currency=None,
        plancher=None,
        plafond=None,
    )
    assert c.covered is False
    assert c.reason == "value_missing"


def test_money_range_no_bounds_passes():
    c = eval_money_range(
        projet_amount=Decimal("123"),
        projet_currency="EUR",
        plancher=None,
        plafond=None,
    )
    assert c.covered is True


def test_geo_in_list():
    c = eval_geo(projet_pays_iso2="CI", eligibilite_geo=["CI", "SN", "BJ"])
    assert c.covered is True


def test_geo_case_insensitive():
    c = eval_geo(projet_pays_iso2="ci", eligibilite_geo=["CI"])
    assert c.covered is True


def test_geo_not_in_list():
    c = eval_geo(projet_pays_iso2="FR", eligibilite_geo=["CI", "SN"])
    assert c.covered is False
    assert c.reason == "not_in_list"


def test_geo_no_restriction():
    c = eval_geo(projet_pays_iso2="FR", eligibilite_geo=None)
    assert c.covered is True


def test_geo_missing_value():
    c = eval_geo(projet_pays_iso2=None, eligibilite_geo=["CI"])
    assert c.covered is False
    assert c.reason == "value_missing"


def test_thematique_overlap():
    c = eval_thematique(
        projet_types_impact=["climat", "agroecologie"],
        fonds_thematique=["Climat", "Genre"],
    )
    assert c.covered is True


def test_thematique_no_overlap():
    c = eval_thematique(
        projet_types_impact=["education"],
        fonds_thematique=["climat"],
    )
    assert c.covered is False
    assert c.reason == "no_overlap"


def test_thematique_missing_projet():
    c = eval_thematique(projet_types_impact=None, fonds_thematique=["climat"])
    assert c.covered is False
    assert c.reason == "value_missing"


def test_thematique_no_fonds_constraint():
    c = eval_thematique(projet_types_impact=None, fonds_thematique=None)
    assert c.covered is True


def test_instruments_overlap():
    c = eval_instruments(
        projet_structure=["subvention", "blending"],
        fonds_instruments=["subvention"],
    )
    assert c.covered is True


def test_instruments_no_overlap():
    c = eval_instruments(
        projet_structure=["pret"],
        fonds_instruments=["subvention"],
    )
    assert c.covered is False
    assert c.reason == "no_overlap"


def test_instruments_no_constraint():
    c = eval_instruments(projet_structure=None, fonds_instruments=None)
    assert c.covered is True


def test_instruments_missing_projet_value():
    c = eval_instruments(projet_structure=None, fonds_instruments=["subvention"])
    assert c.covered is False
    assert c.reason == "value_missing"


def test_critere_json_full():
    c = eval_critere_json(
        {
            "code": "esg_score",
            "label": "Score ESG > 60",
            "severity": "blocking",
            "covered": True,
            "source_id": "11111111-1111-1111-1111-111111111111",
        }
    )
    assert c.covered is True
    assert c.code == "esg_score"
    assert c.severity == "blocking"
    assert c.source_id is not None
    assert str(c.source_id) == "11111111-1111-1111-1111-111111111111"


def test_critere_json_default_not_covered():
    c = eval_critere_json({"code": "x", "severity": "warning"})
    assert c.covered is False
    assert c.reason == "not_evaluated"


def test_critere_json_invalid_severity_falls_back_to_warning():
    c = eval_critere_json({"code": "x", "severity": "FOO"})
    assert c.severity == "warning"


def test_critere_json_invalid_source_id_silent():
    c = eval_critere_json({"code": "x", "source_id": "not-a-uuid", "covered": True})
    assert c.source_id is None


def test_score_layer_empty():
    s = score_layer([])
    assert s.score == 100.0
    assert s.couverts == []
    assert s.manquants == []


def test_score_layer_all_covered():
    cs = [
        CritereMatch(code="a", label="A", severity="blocking", covered=True),
        CritereMatch(code="b", label="B", severity="warning", covered=True),
    ]
    s = score_layer(cs)
    assert s.score == 100.0
    assert len(s.couverts) == 2
    assert s.manquants == []


def test_score_layer_blocking_missing_zero():
    cs = [
        CritereMatch(code="a", label="A", severity="blocking", covered=False),
        CritereMatch(code="b", label="B", severity="warning", covered=True),
    ]
    s = score_layer(cs)
    assert s.score == 0.0


def test_score_layer_partial_warnings():
    cs = [
        CritereMatch(code="a", label="A", severity="warning", covered=True),
        CritereMatch(code="b", label="B", severity="warning", covered=False),
        CritereMatch(code="c", label="C", severity="warning", covered=True),
        CritereMatch(code="d", label="D", severity="warning", covered=True),
    ]
    s = score_layer(cs)
    assert s.score == 75.0
    assert len(s.couverts) == 3
    assert len(s.manquants) == 1


def test_layer_score_dataclass_immutable():
    s = LayerScore(score=50.0, couverts=[], manquants=[])
    with pytest.raises((AttributeError, Exception)):  # noqa: B017 — frozen dataclass
        s.score = 99.0  # type: ignore[misc]
