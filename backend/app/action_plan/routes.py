"""F31 — Routeur FastAPI du module Plan d'Action (PME).

Endpoints :
* ``POST /me/action-plan/generate?horizon=...`` (201 / 422)
* ``GET /me/action-plan`` (200 / 404)
* ``PATCH /me/action-plan/steps/{step_id}`` (200 / 404 / 422)

Toutes les routes sont protégées par ``get_current_pme`` (rôle pme + RLS posée
sur la session via ``SET LOCAL`` dans le middleware F02).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.action_plan.enums import VALID_HORIZONS
from app.action_plan.schemas import (
    ActionPlanRead,
    ActionStepPatch,
    ActionStepRead,
)
from app.action_plan.service import (
    ActionPlanService,
    InvalidHorizonError,
    NoScoreCalculationError,
    StepNotFoundError,
)
from app.auth.dependencies import get_current_pme
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(prefix="/me/action-plan", tags=["action-plan"])


def _serialize_plan(plan) -> ActionPlanRead:  # noqa: ANN001 — ORM
    """Sérialise un ActionPlan ORM (avec ses steps) en schema Pydantic."""
    steps_sorted = sorted(
        plan.steps,
        key=lambda s: (
            {"haute": 0, "moyenne": 1, "basse": 2}.get(str(s.priority), 3),
            s.horizon_at,
        ),
    )
    return ActionPlanRead(
        id=plan.id,
        account_id=plan.account_id,
        horizon_months=plan.horizon_months,
        version=plan.version,
        score_calculation_id=plan.score_calculation_id,
        generated_at=plan.generated_at,
        generated_by_user_id=plan.generated_by_user_id,
        steps=[ActionStepRead.model_validate(s) for s in steps_sorted],
    )


@router.post(
    "/generate",
    response_model=ActionPlanRead,
    status_code=status.HTTP_201_CREATED,
    summary="Génère (ou régénère) le plan d'action de la PME courante.",
)
def generate_action_plan(
    horizon: Annotated[
        int,
        Query(description="Horizon en mois (6, 12 ou 24)", ge=6, le=24),
    ],
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> ActionPlanRead:
    if horizon not in VALID_HORIZONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"horizon doit être dans {sorted(VALID_HORIZONS)}",
        )
    if user.account_id is None:  # pragma: no cover — pme sans compte
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Compte PME requis."
        )
    service = ActionPlanService(db)
    try:
        plan = service.generate(
            account_id=user.account_id,
            horizon_months=horizon,
            user_id=user.id,
        )
    except NoScoreCalculationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    except InvalidHorizonError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)
        ) from exc
    db.commit()
    db.refresh(plan)
    return _serialize_plan(plan)


@router.get(
    "",
    response_model=ActionPlanRead,
    summary="Renvoie le plan d'action courant (dernière version).",
)
def get_current_action_plan(
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> ActionPlanRead:
    if user.account_id is None:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Compte PME requis."
        )
    service = ActionPlanService(db)
    plan = service.get_current(account_id=user.account_id)
    if plan is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Aucun plan d'action généré.",
        )
    return _serialize_plan(plan)


@router.patch(
    "/steps/{step_id}",
    response_model=ActionStepRead,
    summary="Met à jour le statut ou le responsable d'une étape.",
)
def patch_action_step(
    step_id: uuid.UUID,
    patch: ActionStepPatch,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> ActionStepRead:
    if user.account_id is None:  # pragma: no cover
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="Compte PME requis."
        )
    if not patch.has_any_field():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Au moins un champ (status ou responsible_user_id) requis.",
        )
    service = ActionPlanService(db)
    try:
        step = service.update_step(
            step_id=step_id,
            patch=patch,
            user_id=user.id,
            account_id=user.account_id,
        )
    except StepNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Étape introuvable.",
        ) from exc
    db.commit()
    db.refresh(step)
    return ActionStepRead.model_validate(step)
