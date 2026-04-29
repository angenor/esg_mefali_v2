"""F24 — Routes API ``/me/rapports/*`` (PME)."""

from __future__ import annotations

import logging
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.db import get_db
from app.models.account_user import AccountUser
from app.rapports.schemas import (
    RapportCreateIn,
    RapportListOut,
    RapportOut,
)
from app.rapports.service import (
    generate_rapport,
    get_rapport,
    list_rapports,
)
from app.scoring.service import EntityNotAccessible

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me/rapports", tags=["rapports"])


def _to_out(row: dict) -> RapportOut:
    return RapportOut(
        rapport_id=row["rapport_id"],
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        referentiels=row["referentiels"],
        language=row["language"],
        file_size_bytes=row.get("file_size_bytes"),
        generated_at=row["generated_at"],
        download_url=f"/me/rapports/{row['rapport_id']}/download",
    )


@router.post(
    "/conformite",
    response_model=RapportOut,
    status_code=status.HTTP_201_CREATED,
)
def create_rapport(
    body: RapportCreateIn,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> RapportOut:
    """Génère un rapport PDF de conformité ESG pour l'entité demandée."""
    if user.account_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    try:
        result = generate_rapport(
            db,
            account_id=user.account_id,
            entity_type=body.entity_type,
            entity_id=body.entity_id,
            referentiels=body.referentiels,
            language=body.language,
            user_id=user.id,
        )
    except EntityNotAccessible as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="entité hors tenant",
        ) from exc
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc),
        ) from exc
    db.commit()
    return _to_out(result)


@router.get("", response_model=RapportListOut)
def list_my_rapports(
    entity_type: str | None = Query(default=None),
    entity_id: uuid.UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> RapportListOut:
    """Liste les rapports générés par l'account courant."""
    if user.account_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    if entity_type is not None and entity_type not in {"entreprise", "projet"}:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"entity_type invalide: {entity_type}",
        )
    rows = list_rapports(
        db,
        account_id=user.account_id,
        entity_type=entity_type,
        entity_id=entity_id,
        limit=limit,
    )
    items = [_to_out(r) for r in rows]
    return RapportListOut(items=items, total=len(items))


@router.get("/{rapport_id}/download")
def download_rapport(
    rapport_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> FileResponse:
    """Télécharge le PDF d'un rapport (RLS filtré)."""
    if user.account_id is None:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)
    row = get_rapport(
        db, account_id=user.account_id, rapport_id=rapport_id
    )
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    file_path = Path(row["file_path"])
    if not file_path.exists():
        logger.error(
            "rapport.file_missing rapport_id=%s path=%s",
            rapport_id,
            file_path,
        )
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail="fichier rapport introuvable sur disque",
        )
    return FileResponse(
        path=str(file_path),
        media_type="application/pdf",
        filename=f"rapport-esg-{rapport_id}.pdf",
    )
