"""F02 — Dépendances FastAPI : ``get_current_user``, ``get_current_admin``,
``get_current_pme``.

T014 — référence plan.md.

Le middleware ``AuthSessionMiddleware`` a déjà décodé le JWT et placé le payload
sur ``request.state.user_payload``. Cette dépendance charge l'utilisateur et
configure le contexte RLS pour la transaction courante via ``SET LOCAL``.
"""

from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import get_db
from app.models.account_user import AccountUser

_NOT_AUTH = HTTPException(
    status_code=status.HTTP_401_UNAUTHORIZED,
    detail={"code": "not_authenticated", "message": "Authentification requise."},
)
_FORBIDDEN = HTTPException(
    status_code=status.HTTP_403_FORBIDDEN,
    detail={"code": "forbidden", "message": "Accès interdit."},
)


def _set_session_context(
    db: Session, *, user_id: str, account_id: str | None, is_admin: bool
) -> None:
    """Pose les SET LOCAL pour la requête courante (RLS Postgres)."""
    db.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
    if account_id:
        db.execute(text(f"SET LOCAL app.current_account_id = '{account_id}'"))
    db.execute(text(f"SET LOCAL app.is_admin = '{'true' if is_admin else 'false'}'"))


def get_current_user(request: Request, db: Session = Depends(get_db)) -> AccountUser:
    """Retourne l'utilisateur courant ou 401.

    Pose également les SET LOCAL pour RLS sur la session FastAPI.
    """
    payload = getattr(request.state, "user_payload", None)
    if not payload or not payload.get("sub"):
        raise _NOT_AUTH
    user_id = payload["sub"]
    user: AccountUser | None = (
        db.query(AccountUser).filter(AccountUser.id == user_id).first()
    )
    if user is None:
        raise _NOT_AUTH
    is_admin = str(user.role) == "admin"
    _set_session_context(
        db,
        user_id=str(user.id),
        account_id=str(user.account_id) if user.account_id else None,
        is_admin=is_admin,
    )
    return user


def get_current_admin(
    user: AccountUser = Depends(get_current_user),
) -> AccountUser:
    """Exige role=admin, sinon 403."""
    if str(user.role) != "admin":
        raise _FORBIDDEN
    return user


def get_current_pme(
    user: AccountUser = Depends(get_current_user),
) -> AccountUser:
    """Exige role=pme, sinon 403 (utilisé pour endpoints PME-only)."""
    if str(user.role) != "pme":
        raise _FORBIDDEN
    return user
