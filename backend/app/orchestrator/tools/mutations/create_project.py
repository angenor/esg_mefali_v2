"""F17 US2 — Tool ``create_project``.

Schéma Pydantic strict ; handler appelle
``projets.service.create_projet(source_of_change=LLM)``.

Caller : ``register_mutation_tools()`` dans ``mutations/__init__.py``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.audit.schemas import SourceOfChange
from app.orchestrator.tool_registry import tool
from app.orchestrator.tools.mutations._rate_limit import rate_limited
from app.projets.service import create_projet


class MoneyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)


class CreateProjectPayload(BaseModel):
    """Champs minimaux pour créer un projet en brouillon."""

    model_config = ConfigDict(extra="forbid")

    nom: str = Field(min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=4096)
    objectif_environnemental: str | None = Field(default=None, max_length=2048)
    types_impact: list[str] | None = None
    maturite: str | None = None
    montant_recherche: MoneyInput | None = None
    duree_mois: int | None = Field(default=None, ge=0)
    structure_financement_arr: list[str] | None = None
    localisation_pays_iso2: str | None = Field(default=None, min_length=2, max_length=2)
    localisation_ville: str | None = Field(default=None, max_length=256)


def register() -> None:
    tool(
        name="create_project",
        description="Crée un nouveau projet en brouillon pour la PME courante.",
        use_when="La PME exprime un nouveau projet à enregistrer.",
        dont_use_when="Modification d'un projet existant ; usage update_project.",
        schema=CreateProjectPayload,
        positive_examples=(
            {
                "nom": "Panneaux solaires Nord",
                "description": "Installation de 50 MW",
                "montant_recherche": {"amount": "5000000", "currency": "EUR"},
            },
        ),
    )


@rate_limited()
def handle(
    db: Session,
    *,
    account_id: UUID | str,
    user_id: UUID | str,
    payload: CreateProjectPayload,
) -> dict[str, Any]:
    """Exécute la création et retourne un dict structuré.

    Audit log + EventBus sont émis par ``create_projet`` (F12).
    """
    payload_dict = payload.model_dump(exclude_none=True)
    if "montant_recherche" in payload_dict and isinstance(
        payload_dict["montant_recherche"], dict
    ):
        m = payload_dict["montant_recherche"]
        payload_dict["montant_recherche"] = {
            "amount": m["amount"],
            "currency": m["currency"],
        }

    row = create_projet(
        db,
        account_id=account_id,
        user_id=user_id,
        payload=payload_dict,
        source_of_change=SourceOfChange.LLM,
    )
    return {
        "created": True,
        "projet_id": str(row.id),
        "version": row.version,
        "statut": row.statut,
    }


__all__ = ["CreateProjectPayload", "MoneyInput", "handle", "register"]
