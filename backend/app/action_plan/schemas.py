"""F31 — Schemas Pydantic v2 du module Plan d'Action.

Ces schemas miroir le contrat OpenAPI ``contracts/action-plan-api.yaml``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field

from app.action_plan.enums import Category, Horizon, Priority, StepStatus

# --------------------------------------------------------------------------- #
#  DTO interne (générateur)                                                   #
# --------------------------------------------------------------------------- #


@dataclass(frozen=True)
class Gap:
    """Lacune ESG extraite d'un ScoreCalculation (DTO interne).

    Frozen / hashable : sécurise l'usage en sets ou en clés de tri.
    """

    indicator_id: uuid.UUID | None
    indicator_code: str
    indicator_label: str
    score_normalized: Decimal
    pillar: str | None


# --------------------------------------------------------------------------- #
#  Schemas API                                                                #
# --------------------------------------------------------------------------- #


class ActionStepRead(BaseModel):
    """Lecture d'une étape (sortie API)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    plan_id: uuid.UUID
    title: str = Field(min_length=3, max_length=200)
    description: str | None = None
    category: Category
    priority: Priority
    horizon_at: date
    status: StepStatus
    responsible_user_id: uuid.UUID | None = None
    indicateur_id: uuid.UUID | None = None
    source_id: uuid.UUID | None = None
    created_at: datetime
    updated_at: datetime


class ActionStepPatch(BaseModel):
    """Patch partiel d'une étape (PME)."""

    model_config = ConfigDict(extra="forbid")

    status: StepStatus | None = None
    responsible_user_id: uuid.UUID | None = None

    def has_any_field(self) -> bool:
        """Au moins un champ doit être fourni (FR-004)."""
        return bool(self.model_fields_set)


class ActionPlanRead(BaseModel):
    """Lecture d'un plan complet (avec ses étapes)."""

    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    account_id: uuid.UUID
    horizon_months: Horizon
    version: int = Field(ge=1)
    score_calculation_id: uuid.UUID | None = None
    generated_at: datetime
    generated_by_user_id: uuid.UUID | None = None
    steps: list[ActionStepRead] = Field(default_factory=list)
