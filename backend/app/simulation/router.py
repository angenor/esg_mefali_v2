"""F27 - FastAPI router : endpoints PME pour le simulateur de financement."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.db import get_db
from app.models.account_user import AccountUser
from app.simulation import service as sim_service
from app.simulation.schemas import (
    ComparatorRequest,
    SimulationRequest,
)

router = APIRouter(tags=["simulation"])


def _account_uuid(user: AccountUser) -> UUID:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "Compte PME non rattache."},
        )
    aid = user.account_id
    return aid if isinstance(aid, UUID) else UUID(str(aid))


@router.post("/me/simulations")
def create_simulation(
    body: SimulationRequest,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    try:
        result = sim_service.simulate(
            db,
            account_id=_account_uuid(user),
            projet_id=body.projet_id,
            offre_id=body.offre_id,
            hypotheses=body.hypotheses,
        )
    except sim_service.ProjetNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "projet_not_found", "message": str(exc)},
        ) from exc
    except sim_service.OffreNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "offre_not_found", "message": str(exc)},
        ) from exc
    return result.model_dump(mode="json")


@router.post("/me/simulations/comparator")
def create_comparator(
    body: ComparatorRequest,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    try:
        result = sim_service.compare(
            db,
            account_id=_account_uuid(user),
            projet_id=body.projet_id,
            offre_ids=body.offre_ids,
            hypotheses=body.hypotheses,
        )
    except sim_service.ProjetNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "projet_not_found", "message": str(exc)},
        ) from exc
    except sim_service.OffreNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "offre_not_found", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_offre_ids", "message": str(exc)},
        ) from exc
    return result.model_dump(mode="json")
