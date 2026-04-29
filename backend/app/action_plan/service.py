"""F31 — Service applicatif du module Plan d'Action.

Orchestration : lecture du dernier ScoreCalculation, build_steps(), persistance
versionnée d'un ActionPlan + ActionStep, audit append-only.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from app.action_plan.enums import VALID_HORIZONS
from app.action_plan.generator import StepDraft, build_steps
from app.action_plan.schemas import ActionStepPatch
from app.audit import record_audit
from app.audit.schemas import SourceOfChange
from app.models.action_plan import ActionPlan
from app.models.action_step import ActionStep
from app.models.score_calculation import ScoreCalculation

# --------------------------------------------------------------------------- #
#  Exceptions                                                                 #
# --------------------------------------------------------------------------- #


class NoScoreCalculationError(Exception):
    """Aucun ScoreCalculation disponible pour le compte courant (FR-001)."""


class InvalidHorizonError(ValueError):
    """Horizon hors {6, 12, 24}."""


class StepNotFoundError(LookupError):
    """Étape introuvable (RLS ou absente)."""


# --------------------------------------------------------------------------- #
#  Service                                                                    #
# --------------------------------------------------------------------------- #


class ActionPlanService:
    """Service métier F31. Une instance par requête HTTP / unité de travail."""

    def __init__(self, db: Session) -> None:
        self.db = db

    # ------------------------------------------------------------- generate

    def generate(
        self,
        *,
        account_id: uuid.UUID,
        horizon_months: int,
        user_id: uuid.UUID | None,
    ) -> ActionPlan:
        """Génère (ou régénère) le plan courant."""
        if horizon_months not in VALID_HORIZONS:
            raise InvalidHorizonError(
                f"horizon_months must be in {sorted(VALID_HORIZONS)}"
            )

        score = self._load_latest_score(account_id)
        if score is None:
            raise NoScoreCalculationError(
                "Aucun score ESG disponible. Lancez un scoring d'abord."
            )

        next_version = self._lock_and_next_version(account_id)
        now = datetime.now(tz=UTC)

        plan = ActionPlan(
            account_id=account_id,
            horizon_months=horizon_months,
            version=next_version,
            score_calculation_id=score.id,
            generated_at=now,
            generated_by_user_id=user_id,
        )
        self.db.add(plan)
        self.db.flush()  # nécessaire pour récupérer plan.id

        drafts: list[StepDraft] = build_steps(
            score.details_json,
            generated_at=now,
            horizon_months=horizon_months,
        )
        for draft in drafts:
            step = ActionStep(
                plan_id=plan.id,
                title=draft.title,
                description=draft.description,
                category=draft.category.value,
                priority=draft.priority.value,
                horizon_at=draft.horizon_at,
                status="todo",
                indicateur_id=draft.indicateur_id,
                source_id=draft.source_id,
                created_at=now,
                updated_at=now,
            )
            self.db.add(step)
        self.db.flush()

        record_audit(
            self.db,
            entity_type="action_plan",
            entity_id=plan.id,
            field="generate",
            old=None,
            new={
                "version": plan.version,
                "horizon_months": plan.horizon_months,
                "step_count": len(drafts),
                "score_calculation_id": str(score.id),
            },
            source_of_change=SourceOfChange.MANUAL,
            user_id=user_id,
            account_id=account_id,
        )
        return plan

    # ----------------------------------------------------------- get_current

    def get_current(self, *, account_id: uuid.UUID) -> ActionPlan | None:
        """Renvoie le plan le plus récent du compte (ou None)."""
        stmt = (
            select(ActionPlan)
            .where(ActionPlan.account_id == account_id)
            .order_by(ActionPlan.version.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    # ----------------------------------------------------------- update_step

    def update_step(
        self,
        *,
        step_id: uuid.UUID,
        patch: ActionStepPatch,
        user_id: uuid.UUID | None,
        account_id: uuid.UUID,
    ) -> ActionStep:
        """Met à jour une étape (status / responsable). Audit + RLS."""
        step = self.db.get(ActionStep, step_id)
        if step is None:
            raise StepNotFoundError(str(step_id))

        # Defense in depth : RLS Postgres filtre déjà, on revérifie côté Python.
        plan = self.db.get(ActionPlan, step.plan_id)
        if plan is None or plan.account_id != account_id:
            raise StepNotFoundError(str(step_id))

        before: dict[str, Any] = {
            "status": step.status,
            "responsible_user_id": (
                str(step.responsible_user_id) if step.responsible_user_id else None
            ),
        }
        changed_any = False
        if "status" in patch.model_fields_set and patch.status is not None:
            if step.status != patch.status.value:
                step.status = patch.status.value
                changed_any = True
        if "responsible_user_id" in patch.model_fields_set:
            new_resp = patch.responsible_user_id
            if step.responsible_user_id != new_resp:
                step.responsible_user_id = new_resp
                changed_any = True

        if changed_any:
            step.updated_at = datetime.now(tz=UTC)
            self.db.flush()
            after: dict[str, Any] = {
                "status": step.status,
                "responsible_user_id": (
                    str(step.responsible_user_id)
                    if step.responsible_user_id
                    else None
                ),
            }
            record_audit(
                self.db,
                entity_type="action_step",
                entity_id=step.id,
                field="update",
                old=before,
                new=after,
                source_of_change=SourceOfChange.MANUAL,
                user_id=user_id,
                account_id=account_id,
            )
        return step

    # ----------------------------------------------------------- internals

    def _load_latest_score(
        self, account_id: uuid.UUID
    ) -> ScoreCalculation | None:
        stmt = (
            select(ScoreCalculation)
            .where(ScoreCalculation.account_id == account_id)
            .order_by(ScoreCalculation.computed_at.desc())
            .limit(1)
        )
        return self.db.execute(stmt).scalar_one_or_none()

    def _lock_and_next_version(self, account_id: uuid.UUID) -> int:
        """Sérialise les régénérations concurrentes via un advisory lock PG."""
        lock_key = uuid.UUID(int=account_id.int).int & ((1 << 63) - 1)
        self.db.execute(text("SELECT pg_advisory_xact_lock(:k)"), {"k": lock_key})
        max_version = self.db.execute(
            text(
                "SELECT COALESCE(MAX(version), 0) FROM action_plan "
                "WHERE account_id = :acc"
            ),
            {"acc": str(account_id)},
        ).scalar()
        return int(max_version or 0) + 1
