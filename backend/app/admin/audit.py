"""F06 US4 — Wrapper to write admin audit events with ``source_of_change='admin'``."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange


def write_admin_event(
    db: Session,
    *,
    user_id: UUID | str,
    entity_type: str,
    entity_id: UUID | str,
    action: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
) -> None:
    """Persist a row in ``audit_log`` for an admin-side mutation.

    Idempotency : nous loggons le diff complet (before/after) dans le
    champ ``new_value`` et l'``action`` dans ``field``. Le système F04 reste
    le single point of truth ; nous ajoutons uniquement la sémantique
    ``source_of_change='admin'``.
    """
    payload_before = before
    payload_after = {"action": action, "after": after} if after is not None else {"action": action}
    record_audit(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        field=action,
        old=payload_before,
        new=payload_after,
        source_of_change=SourceOfChange.ADMIN,
        user_id=user_id,
    )
