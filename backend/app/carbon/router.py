"""F28 - FastAPI router pour endpoints PME carbone."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.carbon import service as carbon_service
from app.carbon.schemas import CarbonComputeRequest
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(tags=["carbon"])


def _account_uuid(user: AccountUser) -> UUID:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "Compte PME non rattache."},
        )
    aid = user.account_id
    return aid if isinstance(aid, UUID) else UUID(str(aid))


def _user_uuid(user: AccountUser) -> UUID | None:
    uid = getattr(user, "id", None)
    if uid is None:
        return None
    return uid if isinstance(uid, UUID) else UUID(str(uid))


def _serialize(result: dict[str, Any]) -> dict[str, Any]:
    """Decimal -> str pour JSON."""
    out = dict(result)
    out["id"] = str(out["id"])
    out["total_tco2e"] = str(out["total_tco2e"])
    out["by_scope_kgco2e"] = {k: str(v) for k, v in out["by_scope_kgco2e"].items()}
    out["by_category_kgco2e"] = {
        k: str(v) for k, v in out["by_category_kgco2e"].items()
    }
    return out


@router.post("/me/carbon/compute")
def compute_carbon(
    body: CarbonComputeRequest,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    try:
        result = carbon_service.compute_footprint(
            db,
            account_id=_account_uuid(user),
            entreprise_id=None,
            user_id=_user_uuid(user),
            request=body,
        )
    except carbon_service.FactorNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "factor_not_found", "message": str(exc)},
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_input", "message": str(exc)},
        ) from exc
    return _serialize(result)


@router.get("/me/carbon/{year}")
def get_carbon(
    year: int,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    try:
        result = carbon_service.get_latest(
            db, account_id=_account_uuid(user), year=year
        )
    except carbon_service.FootprintNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "footprint_not_found", "message": str(exc)},
        ) from exc
    return _serialize(result)


@router.get("/me/carbon/{year}/reduction-plan")
def get_reduction_plan(
    year: int,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    try:
        return carbon_service.reduction_plan(
            db, account_id=_account_uuid(user), year=year
        )
    except carbon_service.FootprintNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "footprint_not_found", "message": str(exc)},
        ) from exc
