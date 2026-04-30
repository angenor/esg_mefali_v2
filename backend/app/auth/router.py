"""F02 — Router auth : /auth/register, /auth/login, /auth/refresh, /auth/logout,
/auth/forgot-password, /auth/reset-password.

T024, T035, T036, T055, T059.
"""

from __future__ import annotations

import os
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Request, Response, status
from sqlalchemy.orm import Session

from app.auth import service as auth_service
from app.auth.schemas import (
    Error,
    ForgotIn,
    LoginIn,
    MeOut,
    NeutralAck,
    RegisterIn,
    ResetIn,
)
from app.config import get_settings
from app.core.rate_limit import check_rate as _check_rate
from app.core.security import DEFAULT_ACCESS_TTL_SECONDS
from app.db import get_db
from app.middleware.auth_session import (
    ACCESS_COOKIE,
    CSRF_COOKIE,
    REFRESH_COOKIE,
)
from app.models.account_user import AccountUser

router = APIRouter(prefix="/auth", tags=["auth"])

REFRESH_TTL_SECONDS = 60 * 60 * 24 * 30  # 30 jours


def _set_session_cookies(
    resp: Response, *, access: str, refresh: str, csrf: str
) -> None:
    s = get_settings()
    common = {
        "secure": bool(s.COOKIE_SECURE),
        "samesite": "strict",
        "domain": s.COOKIE_DOMAIN if s.COOKIE_DOMAIN != "localhost" else None,
        "path": "/",
    }
    resp.set_cookie(
        ACCESS_COOKIE, access, httponly=True, max_age=DEFAULT_ACCESS_TTL_SECONDS, **common
    )
    resp.set_cookie(
        REFRESH_COOKIE, refresh, httponly=True, max_age=REFRESH_TTL_SECONDS, **common
    )
    # CSRF cookie : NON httpOnly (le JS doit le lire pour le renvoyer)
    resp.set_cookie(
        CSRF_COOKIE,
        csrf,
        httponly=False,
        max_age=DEFAULT_ACCESS_TTL_SECONDS,
        **common,
    )


def _clear_session_cookies(resp: Response) -> None:
    s = get_settings()
    domain = s.COOKIE_DOMAIN if s.COOKIE_DOMAIN != "localhost" else None
    for c in (ACCESS_COOKIE, REFRESH_COOKIE, CSRF_COOKIE):
        resp.delete_cookie(c, path="/", domain=domain)


def _user_to_meout(u: AccountUser) -> MeOut:
    return MeOut(
        user_id=u.id,
        account_id=u.account_id,
        role=str(u.role),  # type: ignore[arg-type]
        email=u.email,
        created_at=u.created_at,
        last_login_at=u.last_login_at,
    )


# ---------- /auth/register ----------


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    response_model=MeOut,
    responses={409: {"model": Error}, 422: {"model": Error}, 429: {"model": Error}},
)
def register(
    request: Request,
    response: Response,
    body: Annotated[RegisterIn, Body()],
    db: Session = Depends(get_db),
) -> MeOut:
    _check_rate(request, "register", os.environ.get("AUTH_REGISTER_RATE", "10/hour"))
    try:
        issued = auth_service.register_pme(
            db, email=body.email, password=body.password
        )
    except auth_service.EmailAlreadyUsedError as exc:
        raise HTTPException(
            status_code=409,
            detail={"code": "email_already_used", "message": "Email déjà utilisé."},
        ) from exc
    db.commit()
    _set_session_cookies(
        response,
        access=issued.access_token,
        refresh=issued.refresh_token_clear,
        csrf=issued.csrf_token,
    )
    return _user_to_meout(issued.user)


# ---------- /auth/login ----------


_INVALID_CREDS = HTTPException(
    status_code=401,
    detail={"code": "invalid_credentials", "message": "Identifiants invalides."},
)


@router.post(
    "/login",
    response_model=MeOut,
    responses={401: {"model": Error}, 429: {"model": Error}},
)
def login_endpoint(
    request: Request,  # noqa: ARG001
    response: Response,
    body: Annotated[LoginIn, Body()],
    db: Session = Depends(get_db),
) -> MeOut:
    _check_rate(request, "login", "5/minute")
    try:
        issued = auth_service.login(db, email=body.email, password=body.password)
    except auth_service.InvalidCredentialsError as exc:
        db.commit()  # commit l'audit log de l'échec
        raise _INVALID_CREDS from exc
    db.commit()
    _set_session_cookies(
        response,
        access=issued.access_token,
        refresh=issued.refresh_token_clear,
        csrf=issued.csrf_token,
    )
    return _user_to_meout(issued.user)


# ---------- /auth/logout ----------


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout_endpoint(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> Response:
    payload = getattr(request.state, "user_payload", None)
    refresh = request.cookies.get(REFRESH_COOKIE)
    if payload and payload.get("sub"):
        from uuid import UUID

        try:
            auth_service.logout(
                db, user_id=UUID(payload["sub"]), refresh_clear=refresh
            )
            db.commit()
        except Exception:  # noqa: BLE001 — logout reste idempotent
            db.rollback()
    _clear_session_cookies(response)
    return Response(status_code=204)


# ---------- /auth/refresh ----------


@router.post(
    "/refresh",
    response_model=MeOut,
    responses={401: {"model": Error}, 429: {"model": Error}},
)
def refresh_endpoint(
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
) -> MeOut:
    _check_rate(request, "refresh", "30/minute")
    refresh_clear = request.cookies.get(REFRESH_COOKIE, "")
    if not refresh_clear:
        raise HTTPException(
            status_code=401,
            detail={"code": "missing_refresh", "message": "Refresh manquant."},
        )
    try:
        issued = auth_service.rotate_refresh(db, refresh_clear=refresh_clear)
    except (auth_service.InvalidRefreshError, auth_service.RefreshReuseDetected) as exc:
        db.commit()
        _clear_session_cookies(response)
        raise HTTPException(
            status_code=401,
            detail={"code": "invalid_refresh", "message": "Refresh invalide."},
        ) from exc
    db.commit()
    _set_session_cookies(
        response,
        access=issued.access_token,
        refresh=issued.refresh_token_clear,
        csrf=issued.csrf_token,
    )
    return _user_to_meout(issued.user)


# ---------- /auth/forgot-password ----------


@router.post(
    "/forgot-password",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=NeutralAck,
)
def forgot_password(
    request: Request,
    body: Annotated[ForgotIn, Body()],
    db: Session = Depends(get_db),
) -> NeutralAck:
    _check_rate(request, "forgot", "5/minute")
    from app.services.email_sender import get_email_sender

    token_clear = auth_service.request_password_reset(db, email=body.email)
    db.commit()
    if token_clear:
        sender = get_email_sender()
        link = auth_service.build_reset_link(token_clear)
        sender.send(
            to=body.email,
            subject="Réinitialisation de votre mot de passe",
            body=f"Pour réinitialiser votre mot de passe, cliquez : {link}\n(valable 30 minutes)",
        )
    return NeutralAck()


# ---------- /auth/reset-password ----------


@router.post("/reset-password", status_code=status.HTTP_204_NO_CONTENT)
def reset_password(
    request: Request,
    body: Annotated[ResetIn, Body()],
    db: Session = Depends(get_db),
) -> Response:
    _check_rate(request, "reset", "10/minute")
    try:
        auth_service.consume_password_reset(
            db, token_clear=body.token, new_password=body.new_password
        )
    except auth_service.InvalidResetTokenError as exc:
        db.rollback()
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_reset_token", "message": "Token invalide."},
        ) from exc
    db.commit()
    return Response(status_code=204)
