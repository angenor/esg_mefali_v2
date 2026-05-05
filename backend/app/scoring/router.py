"""F23 — Routes API ``/me/scoring/*`` (PME)."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.db import get_db
from app.models.account_user import AccountUser
from app.scoring.schemas import (
    ScoreDetailOut,
    ScoreHistoryEntry,
    ScoreHistoryOut,
    ScoreListOut,
    ScoreSummaryOut,
)
from app.scoring.service import (
    EntityNotAccessible,
    ReferentielNotFound,
    compute_and_persist,
    get_latest_score_detail,
    list_history,
    list_latest_scores,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me/scoring", tags=["scoring"])

_ALLOWED_ENTITY_TYPES = {"entreprise", "projet"}


def _validate_entity_type(entity_type: str) -> None:
    if entity_type not in _ALLOWED_ENTITY_TYPES:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"entity_type inconnu: {entity_type}",
        )


@router.get("/{entity_type}/{entity_id}", response_model=ScoreListOut)
def list_scores(
    entity_type: str,
    entity_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> ScoreListOut:
    """Liste le dernier score persisté par référentiel pour une entité."""
    _validate_entity_type(entity_type)
    if user.account_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    rows = list_latest_scores(
        db,
        account_id=user.account_id,
        entity_type=entity_type,
        entity_id=entity_id,
    )
    return ScoreListOut(
        entity_type=entity_type,
        entity_id=entity_id,
        scores=[ScoreSummaryOut(**r) for r in rows],
    )


@router.get(
    "/{entity_type}/{entity_id}/{referentiel_code}",
    response_model=ScoreDetailOut,
)
def get_score_detail(
    entity_type: str,
    entity_id: uuid.UUID,
    referentiel_code: str,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> ScoreDetailOut:
    """Retourne le dernier détail persisté pour ``(entity, referentiel_code)``."""
    _validate_entity_type(entity_type)
    if user.account_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    detail = get_latest_score_detail(
        db,
        account_id=user.account_id,
        entity_type=entity_type,
        entity_id=entity_id,
        referentiel_code=referentiel_code,
    )
    if detail is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    return ScoreDetailOut(**detail)


@router.get(
    "/{entity_type}/{entity_id}/{referentiel_code}/history",
    response_model=ScoreHistoryOut,
)
def list_score_history(
    entity_type: str,
    entity_id: uuid.UUID,
    referentiel_code: str,
    limit: int = Query(12, ge=1, le=50),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> ScoreHistoryOut:
    """F46 — Retourne l'historique des calculs pour ``(entity, referentiel)``."""
    _validate_entity_type(entity_type)
    if user.account_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    try:
        rows = list_history(
            db,
            account_id=user.account_id,
            entity_type=entity_type,
            entity_id=entity_id,
            referentiel_code=referentiel_code,
            limit=limit,
        )
    except ReferentielNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"référentiel non publié: {exc}",
        ) from exc
    except EntityNotAccessible as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="entité hors tenant",
        ) from exc
    return ScoreHistoryOut(
        entity_type=entity_type,
        entity_id=entity_id,
        referentiel_code=referentiel_code,
        entries=[ScoreHistoryEntry(**r) for r in rows],
    )


@router.post(
    "/{entity_type}/{entity_id}/recompute",
    response_model=ScoreDetailOut,
    status_code=status.HTTP_201_CREATED,
)
def recompute_score(
    entity_type: str,
    entity_id: uuid.UUID,
    referentiel: str = Query(..., description="Code du référentiel cible"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> ScoreDetailOut:
    """Force un recalcul ; persiste un nouveau snapshot ``score_calculation``."""
    _validate_entity_type(entity_type)
    if user.account_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    try:
        result = compute_and_persist(
            db,
            account_id=user.account_id,
            entity_type=entity_type,
            entity_id=entity_id,
            referentiel_code=referentiel,
            user_id=user.id,
        )
    except ReferentielNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"référentiel non publié: {exc}",
        ) from exc
    except EntityNotAccessible as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="entité hors tenant",
        ) from exc
    db.commit()
    return ScoreDetailOut(**result)
