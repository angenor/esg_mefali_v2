"""F52 US2 — Service applicatif des préférences de notifications.

Auto-instancie les rows manquants à ``enabled=true`` à la première lecture.
Mise à jour batch atomique avec audit log.
"""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.audit.schemas import SourceOfChange
from app.audit.service import log_settings_change
from app.models.account_user import AccountUser
from app.models.notification_preference import NotificationPreference
from app.notifications.schemas import VALID_NOTIFICATION_KINDS
from app.users.schemas_f52 import (
    NotificationPreferenceItem,
    NotificationPreferencesOut,
)

logger = logging.getLogger(__name__)

CHANNELS: tuple[str, ...] = ("email", "in_app")
# Kinds gérables côté UI ; ``system`` reste imposé serveur (pas de toggle).
DEFAULT_KINDS: tuple[str, ...] = (
    "deadline_j_minus_30",
    "deadline_j_minus_7",
    "deadline_j_minus_1",
    "candidature_inactive",
    "offre_recommandee",
)


def _ensure_defaults(db: Session, *, user: AccountUser) -> list[NotificationPreference]:
    """Crée les rows manquants à ``enabled=true`` (idempotent)."""
    if user.account_id is None:
        return []
    rows = list(
        db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user.id
            )
        ).scalars()
    )
    seen = {(r.kind, r.channel) for r in rows}
    now = datetime.now(UTC)
    added: list[NotificationPreference] = []
    for kind in DEFAULT_KINDS:
        for channel in CHANNELS:
            if (kind, channel) in seen:
                continue
            row = NotificationPreference(
                id=uuid.uuid4(),
                account_id=user.account_id,
                user_id=user.id,
                kind=kind,
                channel=channel,
                enabled=True,
                updated_at=now,
            )
            db.add(row)
            added.append(row)
    if added:
        db.flush()
        rows.extend(added)
    return rows


def get_preferences(db: Session, *, user: AccountUser) -> NotificationPreferencesOut:
    rows = _ensure_defaults(db, user=user)
    items = [
        NotificationPreferenceItem(
            kind=r.kind,  # type: ignore[arg-type]
            channel=r.channel,  # type: ignore[arg-type]
            enabled=bool(r.enabled),
        )
        for r in rows
        if r.kind in VALID_NOTIFICATION_KINDS
    ]
    return NotificationPreferencesOut(items=items)


def update_preferences(
    db: Session,
    *,
    user: AccountUser,
    updates: list[NotificationPreferenceItem],
) -> NotificationPreferencesOut:
    """Applique le batch d'updates dans une transaction unique + audit log.

    Si un row n'existe pas il est créé (UPSERT logique). Audit row par row.
    """
    if user.account_id is None:
        return NotificationPreferencesOut(items=[])

    _ensure_defaults(db, user=user)
    now = datetime.now(UTC)

    existing = {
        (r.kind, r.channel): r
        for r in db.execute(
            select(NotificationPreference).where(
                NotificationPreference.user_id == user.id
            )
        ).scalars()
    }

    for upd in updates:
        if upd.kind not in VALID_NOTIFICATION_KINDS:
            continue
        key = (upd.kind, upd.channel)
        row = existing.get(key)
        if row is None:
            row = NotificationPreference(
                id=uuid.uuid4(),
                account_id=user.account_id,
                user_id=user.id,
                kind=upd.kind,
                channel=upd.channel,
                enabled=upd.enabled,
                updated_at=now,
            )
            db.add(row)
            existing[key] = row
            log_settings_change(
                db,
                user_id=user.id,
                account_id=user.account_id,
                entity="notification_preference",
                entity_id=row.id,
                field="enabled",
                old=None,
                new=upd.enabled,
                source=SourceOfChange.MANUAL,
            )
        elif row.enabled != upd.enabled:
            log_settings_change(
                db,
                user_id=user.id,
                account_id=user.account_id,
                entity="notification_preference",
                entity_id=row.id,
                field="enabled",
                old=bool(row.enabled),
                new=upd.enabled,
                source=SourceOfChange.MANUAL,
            )
            row.enabled = upd.enabled
            row.updated_at = now

    db.flush()
    return get_preferences(db, user=user)


def is_channel_enabled(
    db: Session, *, user_id: uuid.UUID, kind: str, channel: str
) -> bool:
    """Lookup utilisé par le pipeline d'envoi (pre-emit). Default = True."""
    row = db.execute(
        select(NotificationPreference)
        .where(NotificationPreference.user_id == user_id)
        .where(NotificationPreference.kind == kind)
        .where(NotificationPreference.channel == channel)
    ).scalar_one_or_none()
    if row is None:
        return True
    return bool(row.enabled)
