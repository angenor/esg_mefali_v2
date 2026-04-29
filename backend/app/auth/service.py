"""F02 — Service d'authentification : register, login, refresh rotation,
forgot/reset password.

Tâches : T023 (register), T034 (login), T054 (refresh rotation),
T058 (request_password_reset / consume_password_reset).
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta

from sqlalchemy import text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.security import (
    create_access_token,
    generate_csrf_token,
    generate_opaque_token,
    hash_password,
    sha256_hex,
    verify_password,
)
from app.models.account import Account
from app.models.account_user import AccountUser
from app.models.password_reset_token import PasswordResetToken
from app.models.refresh_token import RefreshToken
from app.services.audit import record_event

logger = logging.getLogger(__name__)


REFRESH_TTL = timedelta(days=30)
RESET_TTL = timedelta(minutes=30)


class EmailAlreadyUsedError(Exception):
    pass


class InvalidCredentialsError(Exception):
    """Exception unifiée : email inconnu == mauvais mot de passe."""


class InvalidRefreshError(Exception):
    pass


class RefreshReuseDetected(Exception):
    """Token déjà utilisé : la chaîne entière a été révoquée."""


class InvalidResetTokenError(Exception):
    pass


@dataclass(frozen=True)
class IssuedSession:
    """Tokens émis lors de register/login/refresh."""

    user: AccountUser
    access_token: str
    refresh_token_clear: str
    csrf_token: str


# ---------- Helpers ----------


def _new_refresh_token(
    db: Session, *, user_id: uuid.UUID, parent_id: uuid.UUID | None = None
) -> tuple[RefreshToken, str]:
    clear = generate_opaque_token(32)
    h = sha256_hex(clear)
    now = datetime.now(UTC)
    rt = RefreshToken(
        id=uuid.uuid4(),
        user_id=user_id,
        token_hash=h,
        parent_id=parent_id,
        issued_at=now,
        expires_at=now + REFRESH_TTL,
    )
    db.add(rt)
    db.flush()
    return rt, clear


def _issue_session(db: Session, user: AccountUser) -> IssuedSession:
    access = create_access_token(
        {"sub": str(user.id), "role": str(user.role), "account_id": str(user.account_id) if user.account_id else None}
    )
    _, refresh_clear = _new_refresh_token(db, user_id=user.id)
    return IssuedSession(
        user=user,
        access_token=access,
        refresh_token_clear=refresh_clear,
        csrf_token=generate_csrf_token(),
    )


# ---------- Register ----------


def register_pme(db: Session, *, email: str, password: str) -> IssuedSession:
    """Crée un Account + AccountUser role=pme.

    Lève ``EmailAlreadyUsedError`` si l'email existe déjà.
    """
    existing = db.query(AccountUser).filter(AccountUser.email == email.lower()).first()
    if existing is not None:
        raise EmailAlreadyUsedError(email)

    now = datetime.now(UTC)
    naive = now.replace(tzinfo=None)
    account = Account(id=uuid.uuid4(), name=email.lower(), created_at=naive, updated_at=naive)
    db.add(account)
    db.flush()

    user = AccountUser(
        id=uuid.uuid4(),
        account_id=account.id,
        email=email.lower(),
        password_hash=hash_password(password),
        role="pme",
        version=1,
        created_at=naive,
        updated_at=naive,
    )
    db.add(user)
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raise EmailAlreadyUsedError(email) from exc

    record_event(
        db,
        event_type="auth.register",
        actor_user_id=user.id,
        actor_account_id=account.id,
        payload={"email": email.lower()},
        source_of_change="manual",
    )
    return _issue_session(db, user)


# ---------- Login ----------


def login(db: Session, *, email: str, password: str) -> IssuedSession:
    user = db.query(AccountUser).filter(AccountUser.email == email.lower()).first()
    # Constant-time-ish : on lance toujours un verify_password, même sur user None.
    candidate_hash = user.password_hash if user else "$2b$12$" + ("x" * 53)
    ok = verify_password(password, candidate_hash) if candidate_hash else False
    if not user or not ok:
        record_event(
            db,
            event_type="auth.login.failure",
            actor_user_id=user.id if user else None,
            actor_account_id=user.account_id if user else None,
            payload={"email": email.lower()},
            source_of_change="manual",
        )
        raise InvalidCredentialsError()

    user.last_login_at = datetime.now(UTC)
    db.flush()
    record_event(
        db,
        event_type="auth.login.success",
        actor_user_id=user.id,
        actor_account_id=user.account_id,
        payload={"email": email.lower()},
        source_of_change="manual",
    )
    return _issue_session(db, user)


# ---------- Logout ----------


def logout(db: Session, *, user_id: uuid.UUID, refresh_clear: str | None) -> None:
    """Révoque le refresh token courant si fourni."""
    if refresh_clear:
        h = sha256_hex(refresh_clear)
        rt = db.query(RefreshToken).filter(RefreshToken.token_hash == h).first()
        if rt and rt.revoked_at is None:
            rt.revoked_at = datetime.now(UTC).replace(tzinfo=None)
            rt.revoked_reason = "logout"
            db.flush()
    record_event(
        db,
        event_type="auth.logout",
        actor_user_id=user_id,
        payload={},
        source_of_change="manual",
    )


# ---------- Refresh rotation ----------


def _revoke_chain(db: Session, root_id: uuid.UUID) -> None:
    """Révoque la chaîne complète (parents et enfants) pour reuse_detected."""
    now = datetime.now(UTC)
    db.execute(
        text(
            """
            WITH RECURSIVE ancestors AS (
                SELECT id, parent_id FROM refresh_tokens WHERE id = :root
                UNION
                SELECT rt.id, rt.parent_id
                FROM refresh_tokens rt
                JOIN ancestors a ON a.parent_id = rt.id
            ),
            descendants AS (
                SELECT id, parent_id FROM refresh_tokens WHERE id = :root
                UNION
                SELECT rt.id, rt.parent_id
                FROM refresh_tokens rt
                JOIN descendants d ON rt.parent_id = d.id
            )
            UPDATE refresh_tokens
            SET revoked_at = :now, revoked_reason = 'reuse_detected'
            WHERE id IN (SELECT id FROM ancestors)
               OR id IN (SELECT id FROM descendants)
            """
        ),
        {"root": str(root_id), "now": now},
    )


def rotate_refresh(db: Session, *, refresh_clear: str) -> IssuedSession:
    """Effectue la rotation d'un refresh token. Détecte la réutilisation."""
    h = sha256_hex(refresh_clear)
    rt = db.query(RefreshToken).filter(RefreshToken.token_hash == h).first()
    if rt is None:
        raise InvalidRefreshError("token inconnu")

    now = datetime.now(UTC)
    if rt.revoked_at is not None:
        raise InvalidRefreshError("token révoqué")
    if rt.expires_at < now:
        raise InvalidRefreshError("token expiré")

    if rt.used_at is not None:
        # Vol détecté : révoquer la chaîne entière
        _revoke_chain(db, rt.id)
        record_event(
            db,
            event_type="auth.refresh.reuse_detected",
            actor_user_id=rt.user_id,
            payload={"refresh_id": str(rt.id)},
            source_of_change="manual",
        )
        raise RefreshReuseDetected()

    rt.used_at = now
    db.flush()

    user = db.query(AccountUser).filter(AccountUser.id == rt.user_id).first()
    if user is None:
        raise InvalidRefreshError("utilisateur introuvable")

    access = create_access_token(
        {"sub": str(user.id), "role": str(user.role), "account_id": str(user.account_id) if user.account_id else None}
    )
    _, new_clear = _new_refresh_token(db, user_id=user.id, parent_id=rt.id)
    record_event(
        db,
        event_type="auth.refresh.rotated",
        actor_user_id=user.id,
        payload={"old_id": str(rt.id)},
        source_of_change="manual",
    )
    return IssuedSession(
        user=user,
        access_token=access,
        refresh_token_clear=new_clear,
        csrf_token=generate_csrf_token(),
    )


# ---------- Password reset ----------


def request_password_reset(db: Session, *, email: str) -> str | None:
    """Crée un token de reset si l'email existe.

    Retourne le token clear (pour l'envoi email) ou None si email inconnu.
    L'appelant doit toujours retourner une réponse neutre.
    """
    user = db.query(AccountUser).filter(AccountUser.email == email.lower()).first()
    if user is None:
        record_event(
            db,
            event_type="auth.password_reset.requested_unknown",
            payload={"email": email.lower()},
            source_of_change="manual",
        )
        return None
    clear = generate_opaque_token(32)
    h = sha256_hex(clear)
    now = datetime.now(UTC)
    db.add(
        PasswordResetToken(
            id=uuid.uuid4(),
            user_id=user.id,
            token_hash=h,
            issued_at=now,
            expires_at=now + RESET_TTL,
        )
    )
    db.flush()
    record_event(
        db,
        event_type="auth.password_reset.requested",
        actor_user_id=user.id,
        actor_account_id=user.account_id,
        payload={},
        source_of_change="manual",
    )
    return clear


def build_reset_link(token_clear: str) -> str:
    base = get_settings().RESET_PASSWORD_BASE_URL.rstrip("/")
    return f"{base}?token={token_clear}"


def consume_password_reset(
    db: Session, *, token_clear: str, new_password: str
) -> AccountUser:
    """Consomme un token de reset, met à jour le mot de passe, révoque tous
    les refresh tokens actifs de l'utilisateur.
    """
    h = sha256_hex(token_clear)
    rt = db.query(PasswordResetToken).filter(PasswordResetToken.token_hash == h).first()
    if rt is None:
        raise InvalidResetTokenError("token inconnu")
    now = datetime.now(UTC)
    if rt.consumed_at is not None:
        raise InvalidResetTokenError("token déjà consommé")
    if rt.expires_at < now:
        raise InvalidResetTokenError("token expiré")

    user = db.query(AccountUser).filter(AccountUser.id == rt.user_id).first()
    if user is None:
        raise InvalidResetTokenError("utilisateur introuvable")

    user.password_hash = hash_password(new_password)
    user.updated_at = now.replace(tzinfo=None)
    rt.consumed_at = now

    # Révoque tous les refresh actifs
    db.execute(
        text(
            """
            UPDATE refresh_tokens
            SET revoked_at = :now, revoked_reason = 'password_reset'
            WHERE user_id = :uid AND revoked_at IS NULL
            """
        ),
        {"now": now, "uid": str(user.id)},
    )
    db.flush()
    record_event(
        db,
        event_type="auth.password_reset.consumed",
        actor_user_id=user.id,
        actor_account_id=user.account_id,
        payload={},
        source_of_change="manual",
    )
    return user
