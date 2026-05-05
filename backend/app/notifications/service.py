"""F34 — Service applicatif des notifications PME (étendu F52)."""

from __future__ import annotations

import logging
import uuid
from collections.abc import Iterable
from datetime import UTC, datetime

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.models.notification import Notification
from app.notifications.broker import notifications_broker
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
            notifications_broker.publish(
                account_id=account_id,
                event="notification.read",
                data={"id": str(notif.id)},
            )
        return notif

    @staticmethod
    def mark_all_read(
        db: Session,
        *,
        account_id: uuid.UUID,
        user_id: uuid.UUID | None = None,
        kinds: Iterable[str] | None = None,
    ) -> tuple[int, int]:
        """F52 SC-002 — marque toutes les non-lues comme lues (filtre optionnel).

        Retourne ``(updated_count, unread_count_after)``.

        - ``kinds=None`` : marque tout.
        - ``kinds=[…]`` : restreint au sous-ensemble (les autres restent
          non-lues, donc ``unread_count_after`` peut être > 0).

        Émet un event broker ``notification.bulk_read`` (consommé par SSE).
        """
        kinds_list: list[str] | None = None
        if kinds is not None:
            kinds_list = [k for k in kinds if k in VALID_NOTIFICATION_KINDS]

        now = datetime.now(tz=UTC).replace(tzinfo=None)

        stmt = (
            update(Notification)
            .where(Notification.account_id == account_id)
            .where(Notification.deleted_at.is_(None))
            .where(Notification.read_at.is_(None))
            .values(read_at=now, updated_at=now, version=Notification.version + 1)
        )
        if kinds_list is not None:
            stmt = stmt.where(Notification.kind.in_(kinds_list))

        result = db.execute(stmt)
        updated_count = int(result.rowcount or 0)

        unread_remaining_stmt = (
            select(Notification.id)
            .where(Notification.account_id == account_id)
            .where(Notification.deleted_at.is_(None))
            .where(Notification.read_at.is_(None))
        )
        unread_count_after = len(
            db.execute(unread_remaining_stmt).scalars().all()
        )

        if updated_count > 0:
            try:
                record_audit(
                    db,
                    entity_type="notification",
                    entity_id=account_id,
                    field="bulk_read",
                    old=None,
                    new={
                        "updated": updated_count,
                        "kinds": kinds_list,
                    },
                    source_of_change=SourceOfChange.MANUAL,
                    user_id=str(user_id) if user_id else None,
                    account_id=str(account_id),
                )
            except Exception as exc:  # noqa: BLE001 — audit best-effort
                logger.warning("notification: bulk audit failed: %s", exc)

            notifications_broker.publish(
                account_id=account_id,
                event="notification.bulk_read",
                data={
                    "count": updated_count,
                    "kinds": kinds_list,
                    "unread_count_after": unread_count_after,
                },
            )
        db.flush()
        return updated_count, unread_count_after
