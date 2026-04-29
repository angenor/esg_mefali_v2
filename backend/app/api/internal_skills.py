"""F19 — Endpoint interne ``POST /internal/skill-loader/test`` (FR-009).

Permet aux développeurs de tester le loader + fusion sans passer par le LLM.
Réservé aux environnements dev/test (gardé via ``ENV`` dans la config).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.config import get_settings
from app.db import SessionLocal
from app.skills.fusion import build_prompt
from app.skills.loader import load_active_skills
from app.skills.sources import resolve_sources

router = APIRouter(prefix="/internal/skill-loader", tags=["internal", "skills"])


class SkillLoaderTestBody(BaseModel):
    model_config = ConfigDict(extra="forbid")

    context: dict[str, Any] = Field(default_factory=dict)


class SkillLoaderTestResponse(BaseModel):
    skills: list[dict[str, Any]]
    prompt: str


def _get_session() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _ensure_dev_env() -> None:
    """Refuse l'accès en production."""
    settings = get_settings()
    env = (getattr(settings, "env", None) or "dev").lower()
    if env == "production":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="endpoint disabled in production",
        )


@router.post("/test", response_model=SkillLoaderTestResponse)
def skill_loader_test(
    body: SkillLoaderTestBody,
    session: Session = Depends(_get_session),
) -> SkillLoaderTestResponse:
    """Charge les skills actives pour ``body.context`` et retourne le prompt fusionné."""
    _ensure_dev_env()
    skills = load_active_skills(body.context, session)

    skills_payload = [
        {
            "id": str(s.id),
            "name": s.name,
            "version": s.version,
            "domain": s.domain,
            "tool_whitelist": list(s.tool_whitelist or []),
        }
        for s in skills
    ]

    if not skills:
        return SkillLoaderTestResponse(skills=[], prompt="")

    primary = skills[0]
    from app.models.skill import SkillSource

    rows = (
        session.query(SkillSource.source_id)
        .filter(SkillSource.skill_id == primary.id)
        .all()
    )
    source_ids = [r[0] for r in rows]
    resolved = resolve_sources(source_ids, session)

    prompt = build_prompt(
        global_invariants="Sourçage obligatoire. Multi-tenant. Langue FR.",
        skill_name=primary.name,
        skill_prompt_expert=primary.prompt_expert,
        procedure=primary.procedure,
        sources_resolved=resolved,
        context=body.context,
        tools=list(primary.tool_whitelist or []),
    )
    return SkillLoaderTestResponse(skills=skills_payload, prompt=prompt)


__all__ = ["router"]
