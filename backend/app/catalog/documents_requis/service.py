"""F09 US4 — Service ``document_requis``."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.catalog._shared import (
    archive_row,
    fetch_one,
    insert_row,
    publish_row,
    update_row,
)
from app.catalog.documents_requis.schemas import (
    DocumentRequisCreate,
    DocumentRequisUpdate,
)

TABLE = "document_requis"
JSONB_COLS = {"required_when"}


def create(
    db: Session, payload: DocumentRequisCreate, *, actor_id: uuid.UUID
) -> dict[str, Any]:
    body = payload.model_dump(mode="json")
    return insert_row(
        db, table=TABLE, body=body, actor_id=actor_id, jsonb_cols=JSONB_COLS
    )


def update(
    db: Session,
    id_: str,
    payload: DocumentRequisUpdate,
    *,
    actor_id: uuid.UUID,
    if_match: str | None,
) -> dict[str, Any]:
    body = payload.model_dump(mode="json", exclude_unset=True)
    return update_row(
        db,
        table=TABLE,
        id_=id_,
        payload=body,
        actor_id=actor_id,
        if_match=if_match,
        jsonb_cols=JSONB_COLS,
    )


def publish(db: Session, id_: str, *, actor_id: uuid.UUID, if_match: str | None) -> dict[str, Any]:
    return publish_row(db, table=TABLE, id_=id_, actor_id=actor_id, if_match=if_match)


def archive(db: Session, id_: str, *, actor_id: uuid.UUID, if_match: str | None) -> dict[str, Any]:
    return archive_row(db, table=TABLE, id_=id_, actor_id=actor_id, if_match=if_match)


def get(db: Session, id_: str) -> dict[str, Any] | None:
    return fetch_one(db, TABLE, id_)


def list_documents(
    db: Session,
    *,
    owner_type: str | None = None,
    owner_id: str | None = None,
    type_: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    where: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if owner_type:
        where.append("owner_type = :owner_type")
        params["owner_type"] = owner_type
    if owner_id:
        where.append("owner_id = CAST(:owner_id AS UUID)")
        params["owner_id"] = owner_id
    if type_:
        where.append("type = :type")
        params["type"] = type_
    if status_filter:
        where.append("status = :status")
        params["status"] = status_filter
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = text(
        f"SELECT * FROM {TABLE} {where_sql} "  # noqa: S608
        f"ORDER BY created_at DESC LIMIT :limit OFFSET :offset"
    )
    rows = [dict(r._mapping) for r in db.execute(sql, params).all()]
    total = db.execute(
        text(f"SELECT count(*) FROM {TABLE} {where_sql}"),  # noqa: S608
        {k: v for k, v in params.items() if k not in {"limit", "offset"}},
    ).scalar() or 0
    return {"items": rows, "total": int(total), "limit": limit, "offset": offset}
