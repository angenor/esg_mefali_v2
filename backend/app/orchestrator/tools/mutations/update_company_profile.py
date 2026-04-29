"""F17 US1 — Tool ``update_company_profile``.

Schéma Pydantic strict (extra=forbid, types fermés) ; handler appelle
``entreprise.service.update_partial(source_of_change=LLM)`` qui gère déjà
l'audit log + EventBus.

Caller : ``register_mutation_tools()`` dans ``mutations/__init__.py``.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.audit.schemas import SourceOfChange
from app.entreprise.service import update_partial
from app.orchestrator.tool_registry import tool
from app.orchestrator.tools.mutations._rate_limit import rate_limited


class MoneyInput(BaseModel):
    model_config = ConfigDict(extra="forbid")
    amount: Decimal = Field(ge=0)
    currency: str = Field(min_length=3, max_length=3)


class UpdateCompanyProfileFields(BaseModel):
    """Sous-ensemble des champs entreprise modifiables par le LLM."""

    model_config = ConfigDict(extra="forbid")

    name: str | None = Field(default=None, max_length=512)
    secteur_code: str | None = Field(default=None, max_length=64)
    taille_ca: MoneyInput | None = None
    taille_effectifs: int | None = Field(default=None, ge=0)
    localisation_siege_pays_iso2: str | None = Field(default=None, min_length=2, max_length=2)
    localisation_siege_ville: str | None = Field(default=None, max_length=256)
    zones_operation_pays_iso2: list[str] | None = None
    gouvernance_json: dict[str, Any] | None = None
    pratiques_actuelles_json: dict[str, Any] | None = None


class UpdateCompanyProfilePayload(BaseModel):
    """Payload du tool ``update_company_profile``."""

    model_config = ConfigDict(extra="forbid")

    fields: UpdateCompanyProfileFields
    expected_version: int = Field(ge=1)


def register() -> None:
    tool(
        name="update_company_profile",
        description="Met à jour des champs du profil entreprise de la PME courante.",
        use_when="La PME exprime des données entreprise (CA, effectifs, secteur...).",
        dont_use_when="Mutation sur projet, candidature ou catalogue.",
        schema=UpdateCompanyProfilePayload,
        positive_examples=(
            {"fields": {"taille_effectifs": 75}, "expected_version": 1},
        ),
    )


@rate_limited()
def handle(
    db: Session,
    *,
    account_id: UUID | str,
    user_id: UUID | str,
    payload: UpdateCompanyProfilePayload,
) -> dict[str, Any]:
    """Exécute la mutation et retourne un dict structuré.

    Audit log + EventBus sont émis par ``update_partial`` (F11).
    """
    fields_dict = payload.fields.model_dump(exclude_none=True)
    if not fields_dict:
        return {"updated": False, "reason": "no_fields_provided"}

    if "taille_ca" in fields_dict and isinstance(fields_dict["taille_ca"], dict):
        ca = fields_dict["taille_ca"]
        fields_dict["taille_ca"] = {"amount": ca["amount"], "currency": ca["currency"]}

    row = update_partial(
        db,
        account_id=account_id,
        user_id=user_id,
        expected_version=payload.expected_version,
        payload=fields_dict,
        source_of_change=SourceOfChange.LLM,
    )
    return {
        "updated": True,
        "entreprise_id": str(row.id),
        "version": row.version,
        "fields_changed": list(fields_dict.keys()),
    }


__all__ = [
    "MoneyInput",
    "UpdateCompanyProfileFields",
    "UpdateCompanyProfilePayload",
    "handle",
    "register",
]
