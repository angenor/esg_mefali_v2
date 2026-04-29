"""F28 - Tests bibliotheque actions + generate_plan."""

from __future__ import annotations

from decimal import Decimal

from app.carbon.plan import LIBRARY, generate_plan


def test_library_min_size_and_categories():
    cats = {a.category for a in LIBRARY}
    assert {"energie", "transport", "dechets"}.issubset(cats)
    assert len(LIBRARY) >= 5


def test_generate_plan_filters_by_category():
    plan = generate_plan({"energie": Decimal("1000")})
    assert all(a["category"] == "energie" for a in plan)
    assert len(plan) >= 1


def test_generate_plan_sorted_by_impact_desc():
    plan = generate_plan({"energie": Decimal("1")})
    impacts = [Decimal(str(a["impact_kgco2e_year"])) for a in plan]
    assert impacts == sorted(impacts, reverse=True)


def test_generate_plan_empty_breakdown_returns_full_library():
    plan = generate_plan({})
    assert len(plan) == 5


def test_generate_plan_unknown_category_falls_back():
    plan = generate_plan({"radioactive": Decimal("1")})
    assert len(plan) >= 3


def test_generate_plan_max_actions_cap():
    plan = generate_plan({}, max_actions=2)
    assert len(plan) == 2
