"""F34 — Routes PME ``/me/candidatures``."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.candidatures.schemas import (
    CandidatureRowOut,
    CandidatureStatusOut,
    CandidatureStatusUpdateIn,
)
from app.candidatures.service import (
    CandidatureNotFoundError,
    InvalidCandidatureStatutError,
    list_for_account,
    update_status,
)
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(prefix="/me/candidatures", tags=["candidatures"])


@router.get("", response_model=list[CandidatureRowOut])
def list_my_candidatures(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> list[CandidatureRowOut]:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "Compte PME requis."},
        )
    rows = list_for_account(db, account_id=user.account_id)
    return [CandidatureRowOut.model_validate(r) for r in rows]


@router.patch("/{candidature_id}/status", response_model=CandidatureStatusOut)
def update_my_candidature_status(
    candidature_id: uuid.UUID,
    body: CandidatureStatusUpdateIn,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> CandidatureStatusOut:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "Compte PME requis."},
        )
    try:
        result = update_status(
            db,
            candidature_id=candidature_id,
            account_id=user.account_id,
            user_id=user.id,
            new_statut=body.statut,
        )
    except InvalidCandidatureStatutError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_statut", "message": str(exc)},
        ) from exc
    except CandidatureNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "candidature_not_found"},
        ) from exc
    db.commit()
    return CandidatureStatusOut(
        id=result["id"],
        statut=result["statut"],
        version=result["version"],
        updated_at=result["updated_at"],
    )
