"""F04 — Audit log read service (US3) + helpers F52."""

from __future__ import annotations

import logging
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import AuditLogEntryOut, AuditLogPage, SourceOfChange

logger = logging.getLogger(__name__)

MAX_PAGE_SIZE = 200


def _row_to_out(row: dict[str, Any]) -> AuditLogEntryOut:
    return AuditLogEntryOut(
        id=row["id"],
        user_id=row.get("user_id"),
        account_id=row.get("account_id"),
        timestamp=row["timestamp"],
        entity_type=row["entity_type"],
        entity_id=row["entity_id"],
        field=row.get("field"),
        old_value=row.get("old_value"),
        new_value=row.get("new_value"),
        source_of_change=SourceOfChange(str(row["source_of_change"])),
        request_id=row.get("request_id"),
        ip=str(row["ip"]) if row.get("ip") is not None else None,
    )


def list_entries(  # noqa: PLR0913
    db: Session,
    *,
    entity_type: str | None = None,
    entity_id: UUID | str | None = None,
    source_of_change: SourceOfChange | str | None = None,
    from_ts: datetime | None = None,
    to_ts: datetime | None = None,
    page: int = 1,
    page_size: int = 50,
) -> AuditLogPage:
    """List audit_log entries (RLS-scoped at the DB layer).

    ``page_size`` is clamped to :data:`MAX_PAGE_SIZE` (FR-017, SC-006).
    """
    page = max(1, page)
    page_size = max(1, min(MAX_PAGE_SIZE, page_size))

    where: list[str] = []
    params: dict[str, Any] = {}
    if entity_type:
        where.append("entity_type = :etype")
        params["etype"] = entity_type
    if entity_id:
        where.append("entity_id = CAST(:eid AS UUID)")
        params["eid"] = str(entity_id)
    if source_of_change:
        params["src"] = (
            source_of_change.value
            if isinstance(source_of_change, SourceOfChange)
            else str(source_of_change)
        )
        where.append("source_of_change = CAST(:src AS source_of_change_t)")
    if from_ts:
        where.append('"timestamp" >= :from_ts')
        params["from_ts"] = from_ts
    if to_ts:
        where.append('"timestamp" <= :to_ts')
        params["to_ts"] = to_ts

    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    total_row = db.execute(
        text(f"SELECT COUNT(*) AS c FROM audit_log {where_sql}"),  # noqa: S608
        params,
    ).mappings().first()
    total = int(total_row["c"]) if total_row else 0

    params["limit"] = page_size
    params["offset"] = (page - 1) * page_size
    rows = db.execute(
        text(
            f"SELECT id, user_id, account_id, \"timestamp\", entity_type, "
            f"entity_id, field, old_value, new_value, source_of_change, "
            f"request_id, ip "
            f"FROM audit_log {where_sql} "
            f'ORDER BY "timestamp" DESC, id DESC '
            f"LIMIT :limit OFFSET :offset"  # noqa: S608
        ),
        params,
    ).mappings().all()

    return AuditLogPage(
        items=[_row_to_out(dict(r)) for r in rows],
        total=total,
        page=page,
        page_size=page_size,
    )


# ---------------------------------------------------------------------------
# F52 helpers — settings + deletion (best-effort wrappers around record_audit)
# ---------------------------------------------------------------------------


def log_settings_change(  # noqa: PLR0913
    db: Session,
    *,
    user_id: UUID,
    account_id: UUID | None,
    entity: str,
    entity_id: UUID,
    field: str,
    old: Any,
    new: Any,
    source: SourceOfChange | str = SourceOfChange.MANUAL,
) -> None:
    """Audit générique pour les écrans `/parametres` (P3, FR-013).

    Mute les exceptions internes : un échec d'audit ne doit pas casser la
    mutation métier appelante (cf. ``record_audit`` pour la sémantique).
    """
    try:
        record_audit(
            db,
            entity_type=entity,
            entity_id=entity_id,
            field=field,
            old=old,
            new=new,
            source_of_change=source,
            user_id=user_id,
            account_id=account_id,
        )
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning(
            "audit: log_settings_change failed entity=%s field=%s: %s",
            entity,
            field,
            exc,
        )


def log_deletion_request(
    db: Session,
    *,
    user_id: UUID,
    account_id: UUID,
    request_id: UUID,
    action: str,
    source: SourceOfChange | str = SourceOfChange.MANUAL,
) -> None:
    """Audit dédié au cycle ``account_deletion_request``.

    ``action`` ∈ {created, cancelled, executed}.
    """
    try:
        record_audit(
            db,
            entity_type="account_deletion_request",
            entity_id=request_id,
            field="status",
            old=None,
            new=action,
            source_of_change=source,
            user_id=user_id,
            account_id=account_id,
        )
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning(
            "audit: log_deletion_request failed request=%s action=%s: %s",
            request_id,
            action,
            exc,
        )
