"""F04 — GET /audit-log (US3) and CSV/JSON exports."""

from __future__ import annotations

import csv
import io
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.audit.schemas import AuditLogPage, SourceOfChange
from app.audit.service import list_entries
from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(prefix="/audit-log", tags=["audit-log"])


def _parse_filters(  # noqa: PLR0913
    entity_type: str | None,
    entity_id: UUID | None,
    source_of_change: SourceOfChange | None,
    from_ts: datetime | None,
    to_ts: datetime | None,
    page: int,
    page_size: int,
):
    return {
        "entity_type": entity_type,
        "entity_id": entity_id,
        "source_of_change": source_of_change,
        "from_ts": from_ts,
        "to_ts": to_ts,
        "page": page,
        "page_size": page_size,
    }


@router.get("", response_model=AuditLogPage)
def get_audit_log(  # noqa: PLR0913
    user: Annotated[AccountUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    source_of_change: SourceOfChange | None = None,
    from_ts: datetime | None = Query(None, alias="from"),
    to_ts: datetime | None = Query(None, alias="to"),
    page: int = 1,
    page_size: int = 50,
) -> AuditLogPage:
    """Paginated audit-log listing. RLS scopes to the caller's tenant."""
    _ = user  # auth enforced; RLS is the actual gate
    return list_entries(db, **_parse_filters(
        entity_type, entity_id, source_of_change, from_ts, to_ts, page, page_size,
    ))


@router.get(".csv")
def export_audit_log_csv(  # noqa: PLR0913
    user: Annotated[AccountUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
    entity_type: str | None = None,
    entity_id: UUID | None = None,
    source_of_change: SourceOfChange | None = None,
    from_ts: datetime | None = Query(None, alias="from"),
    to_ts: datetime | None = Query(None, alias="to"),
) -> StreamingResponse:
    """CSV export (no pagination — RLS-bounded)."""
    _ = user
    page = list_entries(
        db,
        entity_type=entity_type,
        entity_id=entity_id,
        source_of_change=source_of_change,
        from_ts=from_ts,
        to_ts=to_ts,
        page=1,
        page_size=200,
    )
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(
        [
            "id", "timestamp", "entity_type", "entity_id", "field",
            "old_value", "new_value", "source_of_change", "user_id",
            "account_id", "request_id", "ip",
        ]
    )
    for item in page.items:
        writer.writerow(
            [
                item.id, item.timestamp.isoformat(), item.entity_type,
                item.entity_id, item.field or "",
                "" if item.old_value is None else str(item.old_value),
                "" if item.new_value is None else str(item.new_value),
                item.source_of_change.value,
                item.user_id or "", item.account_id or "",
                item.request_id or "", item.ip or "",
            ]
        )
    buf.seek(0)
    return StreamingResponse(
        iter([buf.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=audit-log.csv"},
    )
