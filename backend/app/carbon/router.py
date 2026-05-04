"""F28 + F47 - FastAPI router pour endpoints PME carbone."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.carbon import service as carbon_service
from app.carbon.schemas import CarbonComputeRequest, CarbonEditLineRequest
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


@router.get("/me/carbon")
def list_carbon_index(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    limit_years: int = Query(10, ge=1, le=20),
) -> dict[str, Any]:
    """F47 — Index multi-année (lecture seule).

    Retourne la dernière empreinte par year, triée year DESC, limitée à
    ``limit_years`` années. Liste vide si aucune empreinte (pas 404).
    """
    rows = carbon_service.list_index(
        db, account_id=_account_uuid(user), limit_years=limit_years
    )
    return {
        "entries": [
            {
                "footprint_id": str(r["footprint_id"]),
                "year": r["year"],
                "total_tco2e": str(r["total_tco2e"]),
                "computed_at": r["computed_at"].isoformat()
                if hasattr(r["computed_at"], "isoformat")
                else str(r["computed_at"]),
                "version": r["version"],
            }
            for r in rows
        ]
    }


@router.post("/me/carbon/{year}/recompute")
def recompute_carbon(
    year: int,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """F47 — Rejoue compute_footprint avec source_data figé + facteurs courants."""
    try:
        result = carbon_service.recompute(
            db,
            account_id=_account_uuid(user),
            year=year,
            user_id=_user_uuid(user),
        )
    except carbon_service.FootprintNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "footprint_not_found", "message": str(exc)},
        ) from exc
    except carbon_service.FactorNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "factor_not_found", "message": str(exc)},
        ) from exc
    serialized = _serialize(result)
    serialized["previous_footprint_id"] = (
        str(result["previous_footprint_id"])
        if result.get("previous_footprint_id")
        else None
    )
    return serialized


@router.post("/me/carbon/{year}/edit-line")
def edit_carbon_line(
    year: int,
    body: CarbonEditLineRequest,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """F47 — Modifie ou ajoute une ligne, recalcule. Source obligatoire (P1)."""
    try:
        result = carbon_service.edit_line(
            db,
            account_id=_account_uuid(user),
            year=year,
            user_id=_user_uuid(user),
            payload=body,
        )
    except carbon_service.SourceNotVerified as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "source_not_verified", "message": str(exc)},
        ) from exc
    except carbon_service.FootprintNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "footprint_not_found", "message": str(exc)},
        ) from exc
    except carbon_service.FactorNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "factor_not_found", "message": str(exc)},
        ) from exc
    serialized = _serialize(result)
    serialized["previous_footprint_id"] = str(result["previous_footprint_id"])
    serialized["edited_line_code"] = result["edited_line_code"]
    return serialized


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
