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
    SimulationSavedDetailOut,
    SimulationSavedItem,
    SimulationSavedListOut,
    SimulationSaveIn,
    SimulationSaveOut,
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
    # Mode pedagogique F51 : sans projet_id ni offre_id, calcul base sur hypotheses.
    if body.projet_id is None or body.offre_id is None:
        # Acces RLS-scoped (P2) : la dependance get_current_pme garantit account_id.
        _ = _account_uuid(user)
        preview = sim_service.simulate_preview(hypotheses=body.hypotheses)
        return preview.model_dump(mode="json")

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


# ---------- F51 — Save & history ----------


@router.post(
    "/me/simulations/save",
    response_model=SimulationSaveOut,
    status_code=status.HTTP_201_CREATED,
)
def save_simulation_endpoint(
    body: SimulationSaveIn,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> SimulationSaveOut:
    aid = _account_uuid(user)
    try:
        result = sim_service.save_simulation(
            db,
            account_id=aid,
            user_id=user.id,
            label=body.label,
            projet_id=body.projet_id,
            offre_id=body.offre_id,
            hypotheses=dict(body.hypotheses),
            results=dict(body.results),
        )
    except sim_service.QuotaExceededError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "quota_exceeded", "message": "Cap 50 simulations actives."},
        ) from exc
    db.commit()
    return SimulationSaveOut.model_validate(result)


@router.get("/me/simulations", response_model=SimulationSavedListOut)
def list_simulations_endpoint(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = 20,
) -> SimulationSavedListOut:
    aid = _account_uuid(user)
    items = sim_service.list_saved(db, account_id=aid, limit=limit)
    return SimulationSavedListOut(
        items=[SimulationSavedItem.model_validate(i) for i in items],
        count=len(items),
        next_cursor=None,
    )


@router.get(
    "/me/simulations/{sim_id}",
    response_model=SimulationSavedDetailOut,
)
def get_simulation_endpoint(
    sim_id: UUID,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> SimulationSavedDetailOut:
    aid = _account_uuid(user)
    try:
        result = sim_service.get_saved(db, account_id=aid, sim_id=sim_id)
    except sim_service.SimulationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "simulation_not_found"},
        ) from exc
    return SimulationSavedDetailOut.model_validate(result)


@router.delete(
    "/me/simulations/{sim_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def delete_simulation_endpoint(
    sim_id: UUID,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    aid = _account_uuid(user)
    try:
        sim_service.soft_delete_saved(db, account_id=aid, user_id=user.id, sim_id=sim_id)
    except sim_service.SimulationNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "simulation_not_found"},
        ) from exc
    db.commit()
