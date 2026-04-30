"""F31 — Tests unitaires du générateur déterministe (T009)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from decimal import Decimal

import pytest

from app.action_plan.enums import Category, Priority
from app.action_plan.generator import (
    StepDraft,
    _extract_gaps,
    _pillar_to_category,
    _priority_to_horizon_at,
    _severity_to_priority,
    build_steps,
)

NOW = datetime(2026, 4, 29, 10, 0, 0, tzinfo=UTC)


# --------------------------------------------------------------------------- #
#  _severity_to_priority                                                      #
# --------------------------------------------------------------------------- #


@pytest.mark.parametrize(
    "score,expected",
    [
        (Decimal("0.00"), Priority.HAUTE),
        (Decimal("0.20"), Priority.HAUTE),
        (Decimal("0.29"), Priority.HAUTE),
        (Decimal("0.30"), Priority.MOYENNE),
        (Decimal("0.45"), Priority.MOYENNE),
        (Decimal("0.59"), Priority.MOYENNE),
        (Decimal("0.60"), Priority.BASSE),
        (Decimal("0.70"), Priority.BASSE),
        (Decimal("1.00"), Priority.BASSE),
    ],
)
def test_severity_to_priority_thresholds(score: Decimal, expected: Priority) -> None:
    assert _severity_to_priority(score) == expected


# --------------------------------------------------------------------------- #
#  _priority_to_horizon_at                                                    #
# --------------------------------------------------------------------------- #


def test_priority_to_horizon_at_haute_is_third() -> None:
    d = _priority_to_horizon_at(NOW, 12, Priority.HAUTE)
    # 12 mois * 30 / 3 = 120 jours
    assert d.isoformat() == "2026-08-27"


def test_priority_to_horizon_at_moyenne_is_half() -> None:
    d = _priority_to_horizon_at(NOW, 12, Priority.MOYENNE)
    # 12 mois * 30 / 2 = 180 jours
    assert d.isoformat() == "2026-10-26"


def test_priority_to_horizon_at_basse_is_full() -> None:
    d = _priority_to_horizon_at(NOW, 12, Priority.BASSE)
    # 12 mois * 30 = 360 jours
    assert d.isoformat() == "2027-04-24"


# --------------------------------------------------------------------------- #
#  _pillar_to_category                                                        #
# --------------------------------------------------------------------------- #


def test_pillar_to_category_environnement_emission_returns_carbone() -> None:
    assert _pillar_to_category("environnement", "ESG-GES-1") == Category.CARBONE


def test_pillar_to_category_environnement_non_emission_returns_esg() -> None:
    assert _pillar_to_category("environnement", "ESG-EAU") == Category.ESG


def test_pillar_to_category_social_returns_esg() -> None:
    assert _pillar_to_category("social", "S-1") == Category.ESG


def test_pillar_to_category_unknown_returns_esg() -> None:
    assert _pillar_to_category(None, "X") == Category.ESG


# --------------------------------------------------------------------------- #
#  _extract_gaps                                                              #
# --------------------------------------------------------------------------- #


def test_extract_gaps_handles_none() -> None:
    assert _extract_gaps(None) == []


def test_extract_gaps_handles_missing_key() -> None:
    assert _extract_gaps({"score_global": 0.4}) == []


def test_extract_gaps_handles_non_list_gaps() -> None:
    assert _extract_gaps({"gaps": "oops"}) == []


def test_extract_gaps_skips_malformed_entries() -> None:
    payload = {
        "gaps": [
            "not a dict",
            {"score_normalized": "not-a-number"},
            {"indicator_code": "OK", "score_normalized": "0.2"},
        ]
    }
    gaps = _extract_gaps(payload)
    assert len(gaps) == 1
    assert gaps[0].indicator_code == "OK"


def test_extract_gaps_parses_full_entry() -> None:
    ind_id = uuid.uuid4()
    payload = {
        "gaps": [
            {
                "indicator_id": str(ind_id),
                "indicator_code": "ESG-E1",
                "indicator_label": "Émissions Scope 1",
                "score_normalized": "0.15",
                "pillar": "environnement",
            }
        ]
    }
    gaps = _extract_gaps(payload)
    assert len(gaps) == 1
    g = gaps[0]
    assert g.indicator_id == ind_id
    assert g.indicator_code == "ESG-E1"
    assert g.score_normalized == Decimal("0.15")
    assert g.pillar == "environnement"


# --------------------------------------------------------------------------- #
#  build_steps                                                                #
# --------------------------------------------------------------------------- #


def test_build_steps_empty_gaps_returns_default_review_step() -> None:
    drafts = build_steps(None, generated_at=NOW, horizon_months=12)
    assert len(drafts) == 1
    assert drafts[0].title == "Revue annuelle ESG"
    assert drafts[0].priority == Priority.MOYENNE
    assert drafts[0].category == Category.ESG


def test_build_steps_one_high_severity_gap() -> None:
    payload = {
        "gaps": [
            {
                "indicator_id": str(uuid.uuid4()),
                "indicator_code": "ESG-GES-1",
                "indicator_label": "Émissions Scope 1",
                "score_normalized": "0.10",
                "pillar": "environnement",
            }
        ]
    }
    drafts = build_steps(payload, generated_at=NOW, horizon_months=12)
    assert len(drafts) == 1
    d = drafts[0]
    assert d.priority == Priority.HAUTE
    assert d.category == Category.CARBONE
    assert "ESG-GES-1" in d.title


def test_build_steps_sort_priority_descending() -> None:
    payload = {
        "gaps": [
            {"indicator_code": "B", "score_normalized": "0.65", "pillar": "social"},
            {"indicator_code": "A", "score_normalized": "0.10", "pillar": "social"},
            {"indicator_code": "C", "score_normalized": "0.45", "pillar": "social"},
        ]
    }
    drafts = build_steps(payload, generated_at=NOW, horizon_months=12)
    priorities = [d.priority for d in drafts]
    assert priorities == [Priority.HAUTE, Priority.MOYENNE, Priority.BASSE]


def test_build_steps_is_deterministic() -> None:
    payload = {
        "gaps": [
            {"indicator_code": "X", "score_normalized": "0.20", "pillar": "social"},
            {"indicator_code": "Y", "score_normalized": "0.55", "pillar": "social"},
        ]
    }
    a = build_steps(payload, generated_at=NOW, horizon_months=24)
    b = build_steps(payload, generated_at=NOW, horizon_months=24)
    assert a == b


def test_build_steps_step_count_matches_gap_count_when_at_least_one() -> None:
    n = 7
    payload = {
        "gaps": [
            {
                "indicator_code": f"I{i}",
                "score_normalized": "0.20",
                "pillar": "social",
            }
            for i in range(n)
        ]
    }
    drafts = build_steps(payload, generated_at=NOW, horizon_months=6)
    assert len(drafts) == n
    for d in drafts:
        assert isinstance(d, StepDraft)
        assert 3 <= len(d.title) <= 200
