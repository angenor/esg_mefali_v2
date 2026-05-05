"""F25 — FastAPI router: endpoints PME pour le matching projet <-> offre."""

from __future__ import annotations

from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, status
from pydantic import BaseModel, ConfigDict
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.db import get_db
from app.matching import candidature_service
from app.matching import service as matching_service
from app.matching.schemas import OffreDetailOut, OffreFilters, OffreListItem, OffreListOut
from app.models.account_user import AccountUser

router = APIRouter(tags=["matching"])


class CandidatureCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    offre_id: UUID


def _account_uuid(user: AccountUser) -> UUID:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "Compte PME non rattaché."},
        )
    aid = user.account_id
    return aid if isinstance(aid, UUID) else UUID(str(aid))


@router.get("/me/projets/{projet_id}/matching")
def list_matching(
    projet_id: UUID,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    limit: int = Query(10, ge=1, le=50),
) -> dict[str, Any]:
    try:
        items = matching_service.match(
            db,
            account_id=_account_uuid(user),
            projet_id=projet_id,
            max=limit,
        )
    except matching_service.ProjetNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "projet_not_found", "message": str(exc)},
        ) from exc
    payload = [matching_service.serialize_offer_match(it) for it in items]
    return {"items": payload, "count": len(payload)}


@router.get("/me/projets/{projet_id}/matching/{offre_id}")
def get_matching_detail(
    projet_id: UUID,
    offre_id: UUID,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    try:
        detail = matching_service.detail(
            db,
            account_id=_account_uuid(user),
            projet_id=projet_id,
            offre_id=offre_id,
        )
    except matching_service.ProjetNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "projet_not_found", "message": str(exc)},
        ) from exc
    except matching_service.OffreNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "offre_not_found", "message": str(exc)},
        ) from exc
    return matching_service.serialize_match_detail(detail)


@router.get("/me/fonds/{fonds_id}/intermediaires-comparator")
def comparator_endpoint(
    fonds_id: UUID,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    projet_id: UUID = Query(...),
    limit: int = Query(5, ge=1, le=20),
) -> dict[str, Any]:
    try:
        rows = matching_service.comparator(
            db,
            account_id=_account_uuid(user),
            fonds_id=fonds_id,
            projet_id=projet_id,
            limit=limit,
        )
    except matching_service.ProjetNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "projet_not_found", "message": str(exc)},
        ) from exc
    return {
        "fonds_id": str(fonds_id),
        "items": [matching_service.serialize_comparator_row(r) for r in rows],
        "count": len(rows),
    }


@router.post(
    "/me/projets/{projet_id}/candidatures",
    status_code=status.HTTP_201_CREATED,
)
def create_candidature_endpoint(
    projet_id: UUID,
    body: CandidatureCreate,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    try:
        result = candidature_service.create_candidature(
            db,
            account_id=_account_uuid(user),
            projet_id=projet_id,
            offre_id=body.offre_id,
            user_id=user.id if isinstance(user.id, UUID) else UUID(str(user.id)),
        )
    except candidature_service.ProjetNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "projet_not_found", "message": str(exc)},
        ) from exc
    except candidature_service.OffreNotFound as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "offre_not_found", "message": str(exc)},
        ) from exc
    db.commit()
    return result


# ----- F51 — Catalogue endpoints (/me/offres) -----


@router.get("/me/offres", response_model=OffreListOut)
def list_offres_endpoint(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    type: str | None = Query(default=None),
    montant_min_eur: int | None = Query(default=None, ge=0),
    montant_max_eur: int | None = Query(default=None, ge=0),
    duree_min_mois: int | None = Query(default=None, ge=1, le=240),
    duree_max_mois: int | None = Query(default=None, ge=1, le=240),
    intermediaire_id: UUID | None = Query(default=None),
    secteur: str | None = Query(default=None, max_length=64),
    q: str | None = Query(default=None, max_length=128),
    limit: int = Query(default=20, ge=1, le=50),
) -> OffreListOut:
    _account_uuid(user)
    try:
        filters = OffreFilters(
            type=type,  # type: ignore[arg-type]
            montant_min_eur=montant_min_eur,
            montant_max_eur=montant_max_eur,
            duree_min_mois=duree_min_mois,
            duree_max_mois=duree_max_mois,
            intermediaire_id=intermediaire_id,
            secteur=secteur,
            q=q,
            limit=limit,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_filter", "message": str(exc)},
        ) from exc

    items = matching_service.list_offres_for_account(
        db,
        account_id=_account_uuid(user),
        filters=filters.model_dump(exclude_none=True),
        limit=filters.limit,
    )
    return OffreListOut(
        items=[OffreListItem.model_validate(it) for it in items],
        count=len(items),
        next_cursor=None,
    )


@router.get("/me/offres/{offre_id}", response_model=OffreDetailOut)
def get_offre_detail_endpoint(
    offre_id: UUID,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> OffreDetailOut:
    detail = matching_service.get_offre_detail(
        db,
        account_id=_account_uuid(user),
        offre_id=offre_id,
    )
    if detail is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "offre_not_found", "message": "Offre introuvable"},
        )
    return OffreDetailOut.model_validate(detail)
