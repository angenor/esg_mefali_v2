"""F09 US5 — Service ``facteur_emission``."""

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
from app.catalog.facteurs_emission.schemas import (
    FacteurEmissionCreate,
    FacteurEmissionUpdate,
)

TABLE = "facteur_emission"
JSONB_COLS: set[str] = set()


def create(
    db: Session, payload: FacteurEmissionCreate, *, actor_id: uuid.UUID
) -> dict[str, Any]:
    body = payload.model_dump(mode="json")
    return insert_row(
        db, table=TABLE, body=body, actor_id=actor_id, jsonb_cols=JSONB_COLS
    )


def update(
    db: Session,
    id_: str,
    payload: FacteurEmissionUpdate,
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
    )


def publish(db: Session, id_: str, *, actor_id: uuid.UUID, if_match: str | None) -> dict[str, Any]:
    return publish_row(db, table=TABLE, id_=id_, actor_id=actor_id, if_match=if_match)


def archive(db: Session, id_: str, *, actor_id: uuid.UUID, if_match: str | None) -> dict[str, Any]:
    return archive_row(db, table=TABLE, id_=id_, actor_id=actor_id, if_match=if_match)


def get(db: Session, id_: str) -> dict[str, Any] | None:
    return fetch_one(db, TABLE, id_)


def list_facteurs(
    db: Session,
    *,
    code: str | None = None,
    pays_iso2: str | None = None,
    scope: str | None = None,
    categorie: str | None = None,
    status_filter: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    where: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if code:
        where.append("code = :code")
        params["code"] = code
    if pays_iso2:
        where.append("pays_iso2 = :pays")
        params["pays"] = pays_iso2
    if scope:
        where.append("scope = :scope")
        params["scope"] = scope
    if categorie:
        where.append("categorie = :categorie")
        params["categorie"] = categorie
    if status_filter:
        where.append("status = :status")
        params["status"] = status_filter
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = text(
        f"SELECT * FROM {TABLE} {where_sql} "  # noqa: S608
        f"ORDER BY code, valid_from_date DESC, id DESC "
        f"LIMIT :limit OFFSET :offset"
    )
    rows = [dict(r._mapping) for r in db.execute(sql, params).all()]
    total = db.execute(
        text(f"SELECT count(*) FROM {TABLE} {where_sql}"),  # noqa: S608
        {k: v for k, v in params.items() if k not in {"limit", "offset"}},
    ).scalar() or 0
    return {"items": rows, "total": int(total), "limit": limit, "offset": offset}
