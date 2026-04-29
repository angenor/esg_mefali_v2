"""F17 US2 + US4 — Tool ``delete_project`` (destructif).

Schéma Pydantic strict avec ``confirmed: bool``. Le décorateur
``@destructive`` court-circuite l'exécution si ``confirmed != True``.

Caller : ``register_mutation_tools()`` dans ``mutations/__init__.py``.
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.audit.schemas import SourceOfChange
from app.orchestrator.tool_registry import tool
from app.orchestrator.tools.mutations._destructive import destructive
from app.orchestrator.tools.mutations._rate_limit import rate_limited
from app.projets.service import delete_projet


class DeleteProjectPayload(BaseModel):
    """Payload du tool ``delete_project``."""

    model_config = ConfigDict(extra="forbid")

    projet_id: UUID
    confirmed: bool = Field(default=False)


def register() -> None:
    tool(
        name="delete_project",
        description="Supprime un projet de la PME courante (action destructive).",
        use_when="La PME demande explicitement la suppression d'un projet.",
        dont_use_when="Modification ou archivage ; usage update_project.",
        schema=DeleteProjectPayload,
        positive_examples=(
            {
                "projet_id": "00000000-0000-0000-0000-000000000001",
                "confirmed": True,
            },
        ),
    )


@rate_limited()
@destructive(
    tool_name="delete_project",
    message="Confirmer la suppression définitive de ce projet ?",
    impact=("Le projet et ses candidatures liées seront supprimés.",),
)
def handle(
    db: Session,
    *,
    account_id: UUID | str,
    user_id: UUID | str,
    payload: DeleteProjectPayload,
) -> dict[str, Any]:
    """Supprime le projet (soft delete) et retourne un dict structuré.

    Audit log + EventBus sont émis par ``delete_projet`` (F12).
    """
    delete_projet(
        db,
        projet_id=payload.projet_id,
        account_id=account_id,
        user_id=user_id,
        confirm=True,
        source_of_change=SourceOfChange.LLM,
    )
    return {"deleted": True, "projet_id": str(payload.projet_id)}


__all__ = ["DeleteProjectPayload", "handle", "register"]
