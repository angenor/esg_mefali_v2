"""Tests F19 — ordre de priorité des skills."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date

from app.skills.priority import compare_skills, domain_priority


@dataclass
class _Skill:
    domain: str


def test_domain_priority_order() -> None:
    assert domain_priority("dossier") < domain_priority("scoring")
    assert domain_priority("scoring") < domain_priority("diagnostic")
    assert domain_priority("diagnostic") < domain_priority("generale")
    assert domain_priority("inconnu") >= domain_priority("generale")


def test_compare_dossier_beats_scoring() -> None:
    a, b = _Skill("dossier"), _Skill("scoring")
    assert compare_skills(a, b) < 0
    assert compare_skills(b, a) > 0


def test_compare_tiebreak_recent_first() -> None:
    a, b = _Skill("diagnostic"), _Skill("diagnostic")
    assert compare_skills(a, b, a_max_date=date(2026, 1, 1), b_max_date=date(2024, 1, 1)) < 0
    assert compare_skills(a, b, a_max_date=date(2024, 1, 1), b_max_date=date(2026, 1, 1)) > 0


def test_compare_tiebreak_none_dates() -> None:
    a, b = _Skill("scoring"), _Skill("scoring")
    assert compare_skills(a, b) == 0
    assert compare_skills(a, b, a_max_date=date(2026, 1, 1)) < 0
    assert compare_skills(a, b, b_max_date=date(2026, 1, 1)) > 0


def test_unknown_domain_goes_last() -> None:
    known = _Skill("generale")
    unknown = _Skill("foo")
    assert compare_skills(known, unknown) <= 0
