"""F34 — Service applicatif des notifications PME."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.models.notification import Notification
from app.notifications.schemas import VALID_NOTIFICATION_KINDS

logger = logging.getLogger(__name__)


class NotificationNotFoundError(LookupError):
    """Notification absente ou n'appartenant pas au compte appelant."""


class InvalidNotificationKindError(ValueError):
    """Tentative de créer une notification avec un ``kind`` hors enum."""


class NotificationService:
    """Service métier F34 — réutilisable par d'autres modules."""

    @staticmethod
    def create_for_account(
        db: Session,
        *,
        account_id: uuid.UUID,
        kind: str,
        title: str,
        body: str | None = None,
        user_id: uuid.UUID | None = None,
        entity_type: str | None = None,
        entity_id: uuid.UUID | None = None,
        payload: dict | None = None,
    ) -> Notification:
        """Crée une notification pour un compte ; valide ``kind``."""
        if kind not in VALID_NOTIFICATION_KINDS:
            raise InvalidNotificationKindError(
                f"kind={kind!r} hors enum: {sorted(VALID_NOTIFICATION_KINDS)}"
            )
        now = datetime.now(tz=UTC).replace(tzinfo=None)
        notif = Notification(
            id=uuid.uuid4(),
            account_id=account_id,
            user_id=user_id,
            kind=kind,
            title=title,
            body=body,
            entity_type=entity_type,
            entity_id=entity_id,
            payload_json=payload,
            read_at=None,
            version=1,
            deleted_at=None,
            created_at=now,
            updated_at=now,
        )
        db.add(notif)
        db.flush()
        return notif

    @staticmethod
    def list_for_account(
        db: Session,
        *,
        account_id: uuid.UUID,
        unread: bool = False,
        limit: int = 50,
        offset: int = 0,
    ) -> list[Notification]:
        """Liste les notifications de la PME, triées par ``created_at`` DESC."""
        capped_limit = max(1, min(200, int(limit)))
        capped_offset = max(0, int(offset))
        stmt = (
            select(Notification)
            .where(Notification.account_id == account_id)
            .where(Notification.deleted_at.is_(None))
            .order_by(Notification.created_at.desc())
            .limit(capped_limit)
            .offset(capped_offset)
        )
        if unread:
            stmt = stmt.where(Notification.read_at.is_(None))
        return list(db.execute(stmt).scalars().all())

    @staticmethod
    def mark_read(
        db: Session,
        *,
        notification_id: uuid.UUID,
        account_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
    ) -> Notification:
        """Idempotent : positionne ``read_at`` si NULL ; raise NotFound sinon."""
        stmt = (
            select(Notification)
            .where(Notification.id == notification_id)
            .where(Notification.account_id == account_id)
            .where(Notification.deleted_at.is_(None))
        )
        notif = db.execute(stmt).scalar_one_or_none()
        if notif is None:
            raise NotificationNotFoundError(str(notification_id))
        if notif.read_at is None:
            now = datetime.now(tz=UTC).replace(tzinfo=None)
            notif.read_at = now
            notif.updated_at = now
            notif.version = (notif.version or 1) + 1
            try:
                record_audit(
                    db,
                    entity_type="notification",
                    entity_id=notif.id,
                    field="read_at",
                    old=None,
                    new=now.isoformat(),
                    source_of_change=SourceOfChange.MANUAL,
                    user_id=str(user_id) if user_id else None,
                    account_id=str(account_id),
                )
            except Exception as exc:  # noqa: BLE001 — audit best-effort
                logger.warning("notification: audit failed: %s", exc)
            db.flush()
        return notif
