"""F19 — Priorité des skills : dossier > scoring > diagnostic > générale.

Tiebreak : sources les plus à jour (max ``date_publi``).
"""

from __future__ import annotations

from datetime import date
from typing import Protocol

DOMAIN_ORDER: tuple[str, ...] = ("dossier", "scoring", "diagnostic", "generale")


def domain_priority(domain: str) -> int:
    """Retourne le rang ordinal du domaine (plus petit = plus prioritaire)."""
    try:
        return DOMAIN_ORDER.index(domain)
    except ValueError:
        return len(DOMAIN_ORDER)  # domaines inconnus en fin de liste


class _SkillLike(Protocol):
    domain: str


def compare_skills(
    a: _SkillLike,
    b: _SkillLike,
    *,
    a_max_date: date | None = None,
    b_max_date: date | None = None,
) -> int:
    """Compare deux skills. Retourne <0 si a passe avant b, >0 sinon, 0 égal.

    1) priorité de domaine ;
    2) tiebreak : skill avec source la plus récente (date_publi max) passe avant.
    """
    pa, pb = domain_priority(a.domain), domain_priority(b.domain)
    if pa != pb:
        return pa - pb
    # Tiebreak : plus récent gagne (donc passe avant → "plus petit")
    if a_max_date is None and b_max_date is None:
        return 0
    if a_max_date is None:
        return 1
    if b_max_date is None:
        return -1
    if a_max_date > b_max_date:
        return -1
    if a_max_date < b_max_date:
        return 1
    return 0


__all__ = ["DOMAIN_ORDER", "compare_skills", "domain_priority"]
