"""F28 - Tests unitaires moteur carbone (pures fonctions)."""

from __future__ import annotations

from decimal import Decimal

import pytest

from app.carbon.engine import FactorRef, compute_line, compute_total


def make_factor(
    *,
    code: str = "ELEC",
    valeur: str = "0.456",
    unite: str = "kWh",
    scope: str = "2",
    categorie: str = "energie",
) -> FactorRef:
    return FactorRef(
        factor_id="11111111-1111-1111-1111-111111111111",
        code=code,
        valeur=Decimal(valeur),
        unite=unite,
        scope=scope,
        categorie=categorie,
        source_id="22222222-2222-2222-2222-222222222222",
        version=1,
    )


def test_compute_line_basic_kgco2e():
    f = make_factor(valeur="0.456")
    line = compute_line(Decimal("1500"), f)
    assert line.kgco2e == Decimal("684.000000")
    assert line.unit == "kWh"
    assert line.code == "ELEC"


def test_compute_line_zero_quantity():
    f = make_factor()
    line = compute_line(Decimal("0"), f)
    assert line.kgco2e == Decimal("0.000000")


def test_compute_line_negative_raises():
    f = make_factor()
    with pytest.raises(ValueError):
        compute_line(Decimal("-1"), f)


def test_compute_total_aggregates_by_scope():
    f1 = make_factor(code="ELEC", valeur="0.4", scope="2", categorie="energie")
    f2 = make_factor(code="DIESEL", valeur="2.5", scope="1", categorie="energie")
    f3 = make_factor(code="DECHETS", valeur="0.5", scope="3", categorie="dechets")
    lines = [
        compute_line(Decimal("100"), f1),
        compute_line(Decimal("10"), f2),
        compute_line(Decimal("20"), f3),
    ]
    totals = compute_total(lines)
    assert totals["total_kgco2e"] == Decimal("75.000000")
    assert totals["total_tco2e"] == Decimal("0.075000")
    assert totals["by_scope_kgco2e"]["1"] == Decimal("25.000000")
    assert totals["by_scope_kgco2e"]["2"] == Decimal("40.000000")
    assert totals["by_scope_kgco2e"]["3"] == Decimal("10.000000")
    assert totals["by_category_kgco2e"]["energie"] == Decimal("65.000000")
    assert totals["by_category_kgco2e"]["dechets"] == Decimal("10.000000")


def test_compute_total_empty():
    totals = compute_total([])
    assert totals["total_kgco2e"] == Decimal("0")
    assert sum(totals["by_scope_kgco2e"].values()) == Decimal("0")


def test_compute_total_unknown_scope_falls_back_to_3():
    f = make_factor(scope="autre")
    line = compute_line(Decimal("1"), f)
    totals = compute_total([line])
    assert totals["by_scope_kgco2e"]["3"] == line.kgco2e
