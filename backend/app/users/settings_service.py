"""F52 US2 — Service applicatif des écrans /parametres.

Fournit :
- ``request_email_change`` / ``verify_email_change`` (TTL 24 h, bcrypt hash).
- ``list_sessions`` / ``revoke_session`` (table ``refresh_tokens``).
- ``request_account_deletion`` / ``cancel_account_deletion`` /
  ``get_active_request`` (workflow J+30 + e-mail).
"""

from __future__ import annotations

import logging
import secrets
import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.audit.schemas import SourceOfChange
from app.audit.service import log_deletion_request, log_settings_change
from app.core.security import hash_password, verify_password
from app.email.sender import ConsoleEmailSender, EmailMessage
from app.models.account_deletion_request import AccountDeletionRequest
from app.models.account_user import AccountUser
from app.models.refresh_token import RefreshToken

logger = logging.getLogger(__name__)


EMAIL_VERIFICATION_TTL = timedelta(hours=24)
DELETION_GRACE_DELAY = timedelta(days=30)


_email_sender = ConsoleEmailSender()


# ---------------------------------------------------------------------------
# E-mail change
# ---------------------------------------------------------------------------


class EmailAlreadyUsedError(Exception):
    pass


class InvalidPasswordError(Exception):
    pass


class TokenInvalidError(Exception):
    pass


def request_email_change(
    db: Session,
    *,
    user: AccountUser,
    new_email: str,
    current_password: str,
) -> tuple[str, datetime, str]:
    """Crée la demande de changement d'e-mail.

    Retourne ``(email_pending, sent_at, raw_token)`` ; ``raw_token`` doit
    être inclus dans le lien envoyé par e-mail (jamais persisté en clair).
    """
    if not user.password_hash or not verify_password(
        current_password, user.password_hash
    ):
        raise InvalidPasswordError()

    new_email_lc = new_email.strip().lower()
    if new_email_lc == (user.email or "").lower():
        # Idempotent : on accepte mais on ne fait rien.
        raise EmailAlreadyUsedError("same_email")

    existing = db.execute(
        select(AccountUser).where(AccountUser.email == new_email_lc)
    ).scalar_one_or_none()
    if existing is not None and existing.id != user.id:
        raise EmailAlreadyUsedError(new_email_lc)

    raw_token = secrets.token_urlsafe(32)
    token_hash = hash_password(raw_token)
    now = datetime.now(UTC)

    old_pending = user.email_pending
    user.email_pending = new_email_lc
    user.email_verification_token_hash = token_hash
    user.email_verification_sent_at = now
    db.flush()

    log_settings_change(
        db,
        user_id=user.id,
        account_id=user.account_id,
        entity="account_user",
        entity_id=user.id,
        field="email_pending",
        old=old_pending,
        new=new_email_lc,
        source=SourceOfChange.MANUAL,
    )

    try:
        _email_sender.send(
            EmailMessage(
                to=new_email_lc,
                subject="Vérification de votre nouvelle adresse e-mail",
                html=(
                    "<p>Confirmez votre nouvelle adresse e-mail en cliquant sur ce lien :</p>"
                    f"<p><code>token={raw_token}</code></p>"
                ),
                text=f"Token de vérification : {raw_token}",
            )
        )
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("email-change: send failed: %s", exc)

    return new_email_lc, now, raw_token


def verify_email_change(
    db: Session, *, user: AccountUser, token: str
) -> str:
    """Valide le token et bascule ``email_pending → email``.

    Lève ``TokenInvalidError`` si :
    - aucun changement en attente,
    - token TTL dépassé (> 24 h),
    - token incorrect.
    """
    if (
        not user.email_pending
        or not user.email_verification_token_hash
        or not user.email_verification_sent_at
    ):
        raise TokenInvalidError("no_pending_change")

    sent_at = user.email_verification_sent_at
    if sent_at.tzinfo is None:
        sent_at = sent_at.replace(tzinfo=UTC)
    if datetime.now(UTC) - sent_at > EMAIL_VERIFICATION_TTL:
        raise TokenInvalidError("token_expired")

    if not verify_password(token, user.email_verification_token_hash):
        raise TokenInvalidError("token_mismatch")

    old_email = user.email
    new_email = user.email_pending
    user.email = new_email
    user.email_pending = None
    user.email_verification_token_hash = None
    user.email_verification_sent_at = None
    db.flush()

    log_settings_change(
        db,
        user_id=user.id,
        account_id=user.account_id,
        entity="account_user",
        entity_id=user.id,
        field="email",
        old=old_email,
        new=new_email,
        source=SourceOfChange.MANUAL,
    )
    return new_email


# ---------------------------------------------------------------------------
# Sessions (refresh_tokens)
# ---------------------------------------------------------------------------


class SessionNotFoundError(LookupError):
    pass


class CurrentSessionRevocationError(ValueError):
    pass


def list_sessions(
    db: Session, *, user: AccountUser, current_session_id: uuid.UUID | None
) -> list[dict]:
    """Liste les sessions actives (non révoquées, non expirées)."""
    now = datetime.now(UTC)
    rows = (
        db.execute(
            select(RefreshToken)
            .where(RefreshToken.user_id == user.id)
            .where(RefreshToken.revoked_at.is_(None))
            .where(RefreshToken.expires_at > now)
            .order_by(RefreshToken.issued_at.desc())
        )
        .scalars()
        .all()
    )
    out: list[dict] = []
    for r in rows:
        out.append(
            {
                "id": r.id,
                "device_label": "Session",
                "ip_country": None,
                "user_agent_summary": None,
                "created_at": r.issued_at,
                "last_seen_at": r.used_at or r.issued_at,
                "is_current": current_session_id is not None
                and r.id == current_session_id,
            }
        )
    return out


def revoke_session(
    db: Session,
    *,
    user: AccountUser,
    session_id: uuid.UUID,
    current_session_id: uuid.UUID | None,
) -> None:
    """Révoque une session (refresh_tokens.revoked_at)."""
    if current_session_id is not None and session_id == current_session_id:
        raise CurrentSessionRevocationError()

    row = db.execute(
        select(RefreshToken)
        .where(RefreshToken.id == session_id)
        .where(RefreshToken.user_id == user.id)
    ).scalar_one_or_none()
    if row is None:
        raise SessionNotFoundError(str(session_id))
    if row.revoked_at is not None:
        return  # idempotent
    now = datetime.now(UTC)
    row.revoked_at = now
    row.revoked_reason = "user_revoked"
    db.flush()
    log_settings_change(
        db,
        user_id=user.id,
        account_id=user.account_id,
        entity="refresh_token",
        entity_id=row.id,
        field="revoked_at",
        old=None,
        new=now.isoformat(),
        source=SourceOfChange.MANUAL,
    )


# ---------------------------------------------------------------------------
# Suppression compte (workflow J+30)
# ---------------------------------------------------------------------------


class ConfirmationMismatchError(ValueError):
    pass


class AlreadyPendingError(ValueError):
    pass


class DeletionRequestNotFoundError(LookupError):
    pass


def _entreprise_raison_sociale(db: Session, account_id: uuid.UUID) -> str | None:
    row = db.execute(
        text(
            """
            SELECT name
            FROM entreprise
            WHERE account_id = CAST(:aid AS UUID) AND deleted_at IS NULL
            ORDER BY updated_at DESC
            LIMIT 1
            """
        ),
        {"aid": str(account_id)},
    ).first()
    return row.name if row else None


def _normalize(s: str | None) -> str:
    if s is None:
        return ""
    return " ".join(s.strip().split()).lower()


def get_active_request(
    db: Session, *, user: AccountUser
) -> AccountDeletionRequest | None:
    if user.account_id is None:
        return None
    return db.execute(
        select(AccountDeletionRequest)
        .where(AccountDeletionRequest.account_id == user.account_id)
        .where(AccountDeletionRequest.status == "pending")
        .order_by(AccountDeletionRequest.requested_at.desc())
    ).scalar_one_or_none()


def request_account_deletion(
    db: Session,
    *,
    user: AccountUser,
    confirmation_text: str,
    reason_motif: str | None,
) -> AccountDeletionRequest:
    if user.account_id is None:
        raise ValueError("user_without_account")

    raison_sociale = _entreprise_raison_sociale(db, user.account_id)
    if not raison_sociale:
        # Si aucune entreprise rattachée, on accepte une chaîne libre non vide
        # (pas de référence à matcher) — sécurité par UX uniquement.
        if not confirmation_text.strip():
            raise ConfirmationMismatchError()
    elif _normalize(confirmation_text) != _normalize(raison_sociale):
        raise ConfirmationMismatchError()

    if get_active_request(db, user=user) is not None:
        raise AlreadyPendingError()

    now = datetime.now(UTC)
    request = AccountDeletionRequest(
        id=uuid.uuid4(),
        account_id=user.account_id,
        user_id=user.id,
        requested_at=now,
        scheduled_for=now + DELETION_GRACE_DELAY,
        status="pending",
        reason_motif=reason_motif,
        confirmation_text=confirmation_text,
    )
    db.add(request)
    try:
        db.flush()
    except IntegrityError as exc:
        # Conflit anti-doublon couvert par index UNIQUE WHERE status='pending'
        db.rollback()
        raise AlreadyPendingError() from exc

    log_deletion_request(
        db,
        user_id=user.id,
        account_id=user.account_id,
        request_id=request.id,
        action="created",
        source=SourceOfChange.MANUAL,
    )

    try:
        _email_sender.send(
            EmailMessage(
                to=user.email,
                subject="Demande de suppression de compte enregistrée",
                html=(
                    "<p>Votre compte sera supprimé le "
                    f"{request.scheduled_for.isoformat()}. Vous pouvez "
                    "annuler à tout moment depuis Paramètres → Suppression.</p>"
                ),
                text=(
                    "Suppression planifiée le "
                    f"{request.scheduled_for.isoformat()}."
                ),
            )
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("deletion: e-mail send failed: %s", exc)

    return request


def cancel_account_deletion(
    db: Session, *, user: AccountUser, request_id: uuid.UUID
) -> AccountDeletionRequest:
    row = db.execute(
        select(AccountDeletionRequest).where(
            AccountDeletionRequest.id == request_id,
            AccountDeletionRequest.user_id == user.id,
        )
    ).scalar_one_or_none()
    if row is None:
        raise DeletionRequestNotFoundError(str(request_id))
    if row.status != "pending":
        raise DeletionRequestNotFoundError("not_pending")
    row.status = "cancelled"
    row.cancelled_at = datetime.now(UTC)
    db.flush()
    log_deletion_request(
        db,
        user_id=user.id,
        account_id=user.account_id or row.account_id,
        request_id=row.id,
        action="cancelled",
        source=SourceOfChange.MANUAL,
    )
    return row


def to_out_dict(request: AccountDeletionRequest) -> dict:
    """Sérialise une demande en payload prêt pour ``AccountDeletionOut``."""
    can_cancel = (
        request.status == "pending"
        and request.scheduled_for > datetime.now(UTC)
    )
    return {
        "id": request.id,
        "status": request.status,
        "requested_at": request.requested_at,
        "scheduled_for": request.scheduled_for,
        "can_cancel": can_cancel,
    }
