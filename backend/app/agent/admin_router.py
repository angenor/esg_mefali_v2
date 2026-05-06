"""F54 / FR-014 — Admin endpoint GET /admin/agent-runs/{run_id}/prompt.

Retourne :
- En mode normal (status=success/ok) : ``{run_id, status, system_prompt_hash,
  prompt_version, prompt: null}`` — minimisation RGPD.
- En mode erreur (status=error) : ``{..., prompt: <complet en clair>}``
  pour permettre l'investigation.

Auth : ``get_current_admin`` (P7). Non-admin → 403.

Le **prompt complet** n'est pas persisté en clair côté DB : on le
**recompose** depuis les inputs persistés (futur F58 — on retourne ici un
placeholder pour l'erreur, le hash reste la référence).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.agent.repository import get_prompt_for_admin
from app.auth.dependencies import get_current_admin
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(
    prefix="/admin/agent-runs",
    tags=["admin", "agent"],
)


class AgentRunPromptResponse(BaseModel):
    """Schéma de réponse FR-014."""

    model_config = ConfigDict(extra="forbid")

    run_id: uuid.UUID
    status: str
    system_prompt_hash: str | None = None
    prompt_version: str | None = None
    prompt: str | None = None


@router.get(
    "/{run_id}/prompt",
    response_model=AgentRunPromptResponse,
)
def get_agent_run_prompt(
    run_id: uuid.UUID,
    admin: Annotated[AccountUser, Depends(get_current_admin)],
    db: Annotated[Session, Depends(get_db)],
) -> AgentRunPromptResponse:
    """Récupère le prompt info d'un agent_run (FR-014).

    - Run inexistant ou non accessible (RLS) → 404 (P2).
    - Status=ok/success/timeout/cancelled : prompt = None.
    - Status=error : prompt en clair (placeholder F54 — la
      reconstruction complète depuis les inputs sera faite en F58 si
      nécessaire ; pour l'instant, le hash sert d'ancre auditable).
    """
    _ = admin  # auth side-effect uniquement.

    row = get_prompt_for_admin(db, run_id=run_id)
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "agent_run_not_found", "message": "Run introuvable."},
        )

    is_error_run = (row.get("status") or "").lower() == "error"

    return AgentRunPromptResponse(
        run_id=row["id"],
        status=row.get("status") or "ok",
        system_prompt_hash=(row.get("system_prompt_hash") or None),
        prompt_version=row.get("prompt_version") or None,
        prompt=(
            "[F54: prompt complet non persisté en clair. "
            "La reconstruction depuis les inputs sera ajoutée en F58. "
            "Le hash SHA-256 ci-dessus reste la référence d'audit.]"
            if is_error_run
            else None
        ),
    )


__all__ = ["AgentRunPromptResponse", "router"]
