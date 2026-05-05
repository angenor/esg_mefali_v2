"""F52 US2 — Routes ``/me/*`` paramètres : e-mail, sessions, suppression compte.

Séparé de ``router.py`` pour minimiser les conflits avec F02/F42 ; monté dans
``app.main`` avec le même tag ``users``.
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, Request, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme, get_current_user
from app.db import get_db
from app.models.account_user import AccountUser
from app.users.schemas_f52 import (
    AccountDeletionCreate,
    AccountDeletionOut,
    AccountDeletionState,
    EmailChangeOut,
    EmailChangeRequest,
    EmailVerifyOut,
    SessionOut,
    SessionsListOut,
)
from app.users.settings_service import (
    AlreadyPendingError,
    ConfirmationMismatchError,
    CurrentSessionRevocationError,
    DeletionRequestNotFoundError,
    EmailAlreadyUsedError,
    InvalidPasswordError,
    SessionNotFoundError,
    TokenInvalidError,
    cancel_account_deletion,
    get_active_request,
    list_sessions,
    request_account_deletion,
    request_email_change,
    revoke_session,
    to_out_dict,
    verify_email_change,
)

router = APIRouter(tags=["users"])


def _current_session_id(request: Request) -> uuid.UUID | None:
    payload = getattr(request.state, "user_payload", None) or {}
    sid = payload.get("sid")
    if not sid:
        return None
    try:
        return uuid.UUID(sid)
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# E-mail change
# ---------------------------------------------------------------------------


@router.post("/me/email-change", response_model=EmailChangeOut, status_code=202)
def email_change(
    body: Annotated[EmailChangeRequest, Body()],
    user: Annotated[AccountUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> EmailChangeOut:
    try:
        email, sent_at, _token = request_email_change(
            db,
            user=user,
            new_email=body.new_email,
            current_password=body.current_password.get_secret_value(),
        )
    except InvalidPasswordError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"code": "invalid_password"},
        ) from exc
    except EmailAlreadyUsedError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "email_already_used"},
        ) from exc
    db.commit()
    return EmailChangeOut(email_pending=email, verification_sent_at=sent_at)


@router.post("/me/email-change/verify", response_model=EmailVerifyOut)
def email_change_verify(
    user: Annotated[AccountUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    token: Annotated[str, Query(min_length=1)],
) -> EmailVerifyOut:
    try:
        new_email = verify_email_change(db, user=user, token=token)
    except TokenInvalidError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": str(exc) or "token_invalid"},
        ) from exc
    db.commit()
    return EmailVerifyOut(email=new_email)


# ---------------------------------------------------------------------------
# Sessions
# ---------------------------------------------------------------------------


@router.get("/me/sessions", response_model=SessionsListOut)
def get_sessions(
    request: Request,
    user: Annotated[AccountUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> SessionsListOut:
    sid = _current_session_id(request)
    items = list_sessions(db, user=user, current_session_id=sid)
    db.commit()
    return SessionsListOut(items=[SessionOut(**it) for it in items])


@router.delete("/me/sessions/{session_id}", status_code=204)
def delete_session(
    session_id: uuid.UUID,
    request: Request,
    user: Annotated[AccountUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    sid = _current_session_id(request)
    try:
        revoke_session(db, user=user, session_id=session_id, current_session_id=sid)
    except CurrentSessionRevocationError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "cannot_revoke_current"},
        ) from exc
    except SessionNotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "session_not_found"},
        ) from exc
    db.commit()


# ---------------------------------------------------------------------------
# Suppression compte
# ---------------------------------------------------------------------------


@router.get("/me/account-deletion", response_model=AccountDeletionState)
def get_account_deletion(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountDeletionState:
    row = get_active_request(db, user=user)
    db.commit()
    if row is None:
        return AccountDeletionState(request=None)
    return AccountDeletionState(request=AccountDeletionOut(**to_out_dict(row)))


@router.post(
    "/me/account-deletion",
    response_model=AccountDeletionState,
    status_code=201,
)
def create_account_deletion(
    body: Annotated[AccountDeletionCreate, Body()],
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> AccountDeletionState:
    try:
        row = request_account_deletion(
            db,
            user=user,
            confirmation_text=body.confirmation_text,
            reason_motif=body.reason_motif,
        )
    except ConfirmationMismatchError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "confirmation_mismatch"},
        ) from exc
    except AlreadyPendingError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={"code": "already_pending"},
        ) from exc
    db.commit()
    return AccountDeletionState(request=AccountDeletionOut(**to_out_dict(row)))


@router.delete(
    "/me/account-deletion/{request_id}",
    status_code=204,
)
def delete_account_deletion(
    request_id: uuid.UUID,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> None:
    try:
        cancel_account_deletion(db, user=user, request_id=request_id)
    except DeletionRequestNotFoundError as exc:
        # 404 si introuvable, 409 si statut ≠ pending
        msg = str(exc)
        code = (
            status.HTTP_409_CONFLICT
            if msg == "not_pending"
            else status.HTTP_404_NOT_FOUND
        )
        raise HTTPException(
            status_code=code,
            detail={"code": "deletion_not_found" if code == 404 else "not_pending"},
        ) from exc
    db.commit()
