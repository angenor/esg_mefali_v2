"""F19 — Loader contextuel des skills (1 à 2 skills max par tour).

Filtres :
- ``status='published'`` ;
- ``activation_rules`` matche le ``context`` ;
- toutes les sources liées sont ``verified``.

Tri : domaine prioritaire puis source la plus récente. Tronque à 2.
"""

from __future__ import annotations

from datetime import date
from functools import cmp_to_key
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.skill import Skill, SkillSource
from app.models.source import Source
from app.skills.activation_rules import matches_context, parse_rules
from app.skills.priority import compare_skills

MAX_SKILLS_PER_TURN = 2


def _all_sources_verified(
    session: Session, skill_id: Any
) -> tuple[bool, date | None]:
    """Retourne (toutes verified, max date_publi). Si aucune source → (True, None).

    Une skill SANS source liée est considérée valide (rare mais possible : skill
    générale sans citations). C'est l'absence de source non-verified qui compte.
    """
    rows = session.execute(
        select(Source.verification_status, Source.date_publi)
        .join(SkillSource, SkillSource.source_id == Source.id)
        .where(SkillSource.skill_id == skill_id)
    ).all()

    if not rows:
        return True, None

    max_date: date | None = None
    for status, dpub in rows:
        if status != "verified":
            return False, None
        if dpub is not None and (max_date is None or dpub > max_date):
            max_date = dpub
    return True, max_date


def load_active_skills(
    context: dict[str, Any], session: Session
) -> list[Skill]:
    """Retourne 0..2 skills actives pour ``context`` (FR-004).

    Args:
        context: dict avec clés possibles ``page``, ``intent``, ``entity_type``,
            ``offre`` (sous-dict ``fonds_code``/``intermediaire_code``).
        session: session SQLAlchemy.
    """
    published = list(
        session.execute(select(Skill).where(Skill.status == "published")).scalars()
    )

    candidates: list[tuple[Skill, date | None]] = []
    for skill in published:
        rules = parse_rules(skill.activation_rules)
        if not matches_context(rules, context):
            continue
        ok, max_date = _all_sources_verified(session, skill.id)
        if not ok:
            continue
        candidates.append((skill, max_date))

    def _cmp(a: tuple[Skill, date | None], b: tuple[Skill, date | None]) -> int:
        return compare_skills(a[0], b[0], a_max_date=a[1], b_max_date=b[1])

    candidates.sort(key=cmp_to_key(_cmp))
    return [s for s, _ in candidates[:MAX_SKILLS_PER_TURN]]


__all__ = ["MAX_SKILLS_PER_TURN", "load_active_skills"]
