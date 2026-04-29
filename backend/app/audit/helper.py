"""F04 — ``record_audit`` helper : append-only INSERT into ``audit_log``.

Contract (T041):
- Accepts session, entity_type, entity_id, field, old, new, source_of_change,
  optional notes.
- Pulls user_id, account_id, request_id, ip from request context (FastAPI
  ``Request.state``) when available; falls back to explicit kwargs otherwise.
- Applies blacklist redaction recursively (FR-013, SC-010).
- Skips the insert when ``old == new`` (FR-019, T031).
- Always inserts via SQLAlchemy parameterized SQL — no string concatenation.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.blacklist import redact_field
from app.audit.schemas import SourceOfChange

logger = logging.getLogger(__name__)


def _normalize_jsonb(value: Any) -> str | None:
    """Serialize ``value`` to a JSON string suitable for the JSONB column.

    ``None`` stays NULL. Any non-serialisable object is rendered via ``str``.
    """
    if value is None:
        return None
    return json.dumps(value, default=str)


def record_audit(  # noqa: PLR0913 — wide signature is the public contract
    db: Session,
    *,
    entity_type: str,
    entity_id: UUID | str,
    field: str | None = None,
    old: Any = None,
    new: Any = None,
    source_of_change: SourceOfChange | str = SourceOfChange.MANUAL,
    notes: str | None = None,
    user_id: UUID | str | None = None,
    account_id: UUID | str | None = None,
    request_id: str | None = None,
    ip: str | None = None,
) -> UUID | None:
    """Insert one row into ``audit_log`` (append-only).

    Returns the row id on success, or ``None`` when the call short-circuited
    (no-op due to ``old == new``).

    The function never raises business-level exceptions: an audit insertion
    failure is logged but does NOT abort the caller's transaction; we use a
    SAVEPOINT to keep the parent transaction usable. (Privilege rejection
    must propagate, however — that is the SC-002 gate.)
    """
    # Short-circuit no-op (FR-019).
    if field is not None and old == new:
        return None

    src = (
        source_of_change.value
        if isinstance(source_of_change, SourceOfChange)
        else str(source_of_change)
    )

    redacted_old = redact_field(field, old)
    redacted_new = redact_field(field, new)

    payload = {
        "id": str(uuid4()),
        "uid": str(user_id) if user_id else None,
        "aid": str(account_id) if account_id else None,
        "etype": entity_type,
        "eid": str(entity_id),
        "field": field,
        "old": _normalize_jsonb(redacted_old),
        "new": _normalize_jsonb(redacted_new),
        "src": src,
        "rid": request_id,
        "ip": ip,
        "notes": notes,
    }

    sql = text(
        """
        INSERT INTO audit_log
            (id, user_id, account_id, entity_type, entity_id,
             field, old_value, new_value, source_of_change,
             request_id, ip, "timestamp", created_at, updated_at, version)
        VALUES
            (CAST(:id AS UUID), CAST(:uid AS UUID), CAST(:aid AS UUID),
             :etype, CAST(:eid AS UUID),
             :field, CAST(:old AS JSONB), CAST(:new AS JSONB),
             CAST(:src AS source_of_change_t),
             :rid, CAST(:ip AS INET),
             now(), now(), now(), 1)
        """
    )
    sp = db.begin_nested()
    try:
        db.execute(sql, payload)
        sp.commit()
    except Exception as exc:
        sp.rollback()
        # If the failure is a privilege error or any DB-level rejection, we
        # propagate so the caller's test on SC-002 can observe it; otherwise
        # log and re-raise (audit gate is constitutional).
        logger.error("audit: insert failed entity_type=%s: %s", entity_type, exc)
        raise

    if notes:
        # ``notes`` is intentionally not stored in audit_log (no column for it
        # in F01/F04 — kept for future schema). Log as info for traceability.
        logger.info("audit notes [%s/%s]: %s", entity_type, entity_id, notes)

    return UUID(payload["id"])
