"""F34/F51 — Routes PME ``/me/candidatures``."""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.candidatures.schemas import (
    CandidatureDetailOut,
    CandidatureRowOut,
    CandidatureStatusOut,
    CandidatureStatusUpdateIn,
    WizardDraftIn,
    WizardDraftOut,
    WizardSubmitIn,
    WizardSubmitOut,
)
from app.candidatures.service import (
    AlreadySubmittedError,
    CandidatureNotFoundError,
    ConfirmationRequiredError,
    IncompleteDossierError,
    InvalidCandidatureStatutError,
    VersionConflictError,
    get_detail,
    list_for_account,
    save_draft,
    submit_with_snapshot,
    update_status,
)
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(prefix="/me/candidatures", tags=["candidatures"])


def _ensure_account(user: AccountUser) -> uuid.UUID:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "Compte PME requis."},
        )
    return user.account_id  # type: ignore[return-value]


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


# ---------- F51 — Wizard endpoints ----------


@router.get("/{candidature_id}", response_model=CandidatureDetailOut)
def get_my_candidature(
    candidature_id: uuid.UUID,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> CandidatureDetailOut:
    aid = _ensure_account(user)
    try:
        detail = get_detail(db, account_id=aid, candidature_id=candidature_id)
    except CandidatureNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "candidature_not_found"},
        ) from exc
    return CandidatureDetailOut.model_validate(detail)


@router.patch("/{candidature_id}/draft", response_model=WizardDraftOut)
def patch_my_candidature_draft(
    candidature_id: uuid.UUID,
    body: WizardDraftIn,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> WizardDraftOut:
    aid = _ensure_account(user)
    try:
        result = save_draft(
            db,
            account_id=aid,
            user_id=user.id,
            candidature_id=candidature_id,
            patch=body.draft_snapshot_json or {},
            expected_version=body.expected_version,
            new_step=body.step_courant,
        )
    except CandidatureNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "candidature_not_found"},
        ) from exc
    except AlreadySubmittedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "already_submitted"},
        ) from exc
    except VersionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "version_conflict",
                "current_version": exc.current_version,
                "current_draft": exc.current_draft,
            },
        ) from exc
    db.commit()
    return WizardDraftOut.model_validate(result)


@router.post("/{candidature_id}/submit", response_model=WizardSubmitOut)
def submit_my_candidature(
    candidature_id: uuid.UUID,
    body: WizardSubmitIn,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> WizardSubmitOut:
    aid = _ensure_account(user)
    try:
        result = submit_with_snapshot(
            db,
            account_id=aid,
            user_id=user.id,
            candidature_id=candidature_id,
            expected_version=body.expected_version,
            confirmed=body.confirmed,
            user_acknowledged_intangible=body.user_acknowledged_intangible,
        )
    except CandidatureNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "candidature_not_found"},
        ) from exc
    except ConfirmationRequiredError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "confirmation_required"},
        ) from exc
    except AlreadySubmittedError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "already_submitted"},
        ) from exc
    except IncompleteDossierError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "incomplete_dossier", "missing": exc.missing},
        ) from exc
    except VersionConflictError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "code": "version_conflict",
                "current_version": exc.current_version,
                "current_draft": exc.current_draft,
            },
        ) from exc
    db.commit()
    return WizardSubmitOut.model_validate(result)
