"""F03 — Routes HTTP catalogue Source.

- ``GET /sources/{id}`` : lecture publique unitaire (FR-004).
- ``GET /sources`` : liste paginée admin only (RBAC F02).
"""

from __future__ import annotations

import uuid
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.db import get_db
from app.schemas.source import (
    SourceList,
    SourceRead,
    SourceVerificationStatus,
)

router = APIRouter(tags=["sources"])

_NOT_FOUND = HTTPException(
    status_code=status.HTTP_404_NOT_FOUND,
    detail={"code": "not_found", "message": "Source introuvable."},
)


def _row_to_source(row) -> SourceRead:
    d = dict(row)
    # Pydantic HttpUrl exige str
    return SourceRead.model_validate(d)


@router.get("/sources/{id}", response_model=SourceRead)
def get_source_by_id(id: uuid.UUID, db: Session = Depends(get_db)) -> SourceRead:
    row = db.execute(
        text(
            "SELECT id, url, title, publisher, version, date_publi, page, section, "
            "captured_at, verified_at, verification_status, notes "
            "FROM source WHERE id = :id"
        ),
        {"id": str(id)},
    ).mappings().first()
    if row is None:
        raise _NOT_FOUND
    return _row_to_source(row)


@router.get("/sources", response_model=SourceList)
def list_sources(
    db: Annotated[Session, Depends(get_db)],
    _admin=Depends(get_current_admin),
    q: str | None = Query(default=None, max_length=256),
    publisher: str | None = Query(default=None, max_length=100),
    status_filter: SourceVerificationStatus | None = Query(default=None, alias="status"),
    limit: int = Query(default=20, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
) -> SourceList:
    where: list[str] = []
    params: dict = {}
    if q:
        where.append("tsv @@ plainto_tsquery('french', :q)")
        params["q"] = q
    if publisher:
        where.append("publisher = :pub")
        params["pub"] = publisher
    if status_filter is not None:
        where.append("verification_status = :st")
        params["st"] = status_filter.value
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    total = db.execute(
        text(f"SELECT COUNT(*) FROM source {where_sql}"), params
    ).scalar() or 0

    rows = db.execute(
        text(
            "SELECT id, url, title, publisher, version, date_publi, page, section, "
            "captured_at, verified_at, verification_status, notes "
            f"FROM source {where_sql} ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
        ),
        {**params, "limit": limit, "offset": offset},
    ).mappings().all()
    items = [_row_to_source(r) for r in rows]
    return SourceList(items=items, total=int(total), limit=limit, offset=offset)
