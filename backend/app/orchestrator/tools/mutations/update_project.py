"""F17 US2 — Tool ``update_project``.

Schéma Pydantic strict ; handler appelle
``projets.service.patch_projet(source_of_change=LLM)``.

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
from app.projets.service import patch_projet


class MoneyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)


class UpdateProjectFields(BaseModel):
    """Champs modifiables sur un projet par le LLM."""

    model_config = ConfigDict(extra="forbid")

    nom: str | None = Field(default=None, min_length=1, max_length=512)
    description: str | None = Field(default=None, max_length=4096)
    objectif_environnemental: str | None = Field(default=None, max_length=2048)
    types_impact: list[str] | None = None
    maturite: str | None = None
    montant_recherche: MoneyInput | None = None
    duree_mois: int | None = Field(default=None, ge=0)
    structure_financement_arr: list[str] | None = None
    localisation_pays_iso2: str | None = Field(default=None, min_length=2, max_length=2)
    localisation_ville: str | None = Field(default=None, max_length=256)
    statut: str | None = None


class UpdateProjectPayload(BaseModel):
    """Payload du tool ``update_project`` : id + version + champs partiels."""

    model_config = ConfigDict(extra="forbid")

    projet_id: UUID
    expected_version: int = Field(ge=1)
    fields: UpdateProjectFields


def register() -> None:
    tool(
        name="update_project",
        description="Met à jour partiellement un projet existant de la PME courante.",
        use_when="La PME ajuste les caractéristiques d'un projet déjà créé.",
        dont_use_when="Création d'un nouveau projet ou suppression.",
        schema=UpdateProjectPayload,
        positive_examples=(
            {
                "projet_id": "00000000-0000-0000-0000-000000000001",
                "expected_version": 1,
                "fields": {"nom": "Panneaux solaires Nord (révisé)"},
            },
        ),
    )


@rate_limited()
def handle(
    db: Session,
    *,
    account_id: UUID | str,
    user_id: UUID | str,
    payload: UpdateProjectPayload,
) -> dict[str, Any]:
    """Exécute la mise à jour partielle et retourne un dict structuré.

    Audit log + EventBus sont émis par ``patch_projet`` (F12).
    """
    fields_dict = payload.fields.model_dump(exclude_none=True)
    if not fields_dict:
        return {"updated": False, "reason": "no_fields_provided"}

    if "montant_recherche" in fields_dict and isinstance(
        fields_dict["montant_recherche"], dict
    ):
        m = fields_dict["montant_recherche"]
        fields_dict["montant_recherche"] = {
            "amount": m["amount"],
            "currency": m["currency"],
        }

    row = patch_projet(
        db,
        projet_id=payload.projet_id,
        account_id=account_id,
        user_id=user_id,
        expected_version=payload.expected_version,
        payload=fields_dict,
        source_of_change=SourceOfChange.LLM,
    )
    return {
        "updated": True,
        "projet_id": str(row.id),
        "version": row.version,
        "fields_changed": list(fields_dict.keys()),
    }


__all__ = [
    "MoneyInput",
    "UpdateProjectFields",
    "UpdateProjectPayload",
    "handle",
    "register",
]
