"""F09 — Helpers partagés (CRUD générique pour critere/document_requis/facteur_emission).

Ces entités ont une seule colonne ``source_id`` (pas de junction) — on peut donc
réutiliser ``app.api.admin._helpers`` (F08) qui gère INSERT/UPDATE/publish + audit.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.admin.audit import write_admin_event
from app.admin.etag import assert_version_match, parse_if_match
from app.admin.publish import verify_sources_or_422
from app.admin.registry import EntitySpec, registry


def _serialize_value(v: Any) -> Any:
    if isinstance(v, uuid.UUID):
        return str(v)
    if hasattr(v, "isoformat"):
        return v.isoformat()
    if isinstance(v, list):
        return [_serialize_value(x) for x in v]
    if isinstance(v, dict):
        return {k: _serialize_value(x) for k, x in v.items()}
    return v


def serialize_row(row: dict[str, Any]) -> dict[str, Any]:
    return {k: _serialize_value(v) for k, v in row.items() if not k.startswith("_")}


def fetch_one(db: Session, table: str, id_: str) -> dict[str, Any] | None:
    row = db.execute(
        text(f"SELECT * FROM {table} WHERE id = CAST(:id AS UUID)"),  # noqa: S608
        {"id": id_},
    ).first()
    return dict(row._mapping) if row else None


def insert_row(
    db: Session,
    *,
    table: str,
    body: dict[str, Any],
    actor_id: uuid.UUID,
    jsonb_cols: set[str] | None = None,
) -> dict[str, Any]:
    body = dict(body)
    body.setdefault("status", "draft")
    body.setdefault("version", 1)
    body["created_by"] = str(actor_id)
    jsonb_cols = jsonb_cols or set()

    for k in jsonb_cols:
        if k in body and body[k] is not None and not isinstance(body[k], str):
            body[k] = json.dumps(body[k], default=_json_default)
    # convert UUIDs
    for k, v in list(body.items()):
        if isinstance(v, uuid.UUID):
            body[k] = str(v)

    cols = list(body.keys())
    placeholders = ", ".join(f":{c}" for c in cols)
    sql = text(
        f"INSERT INTO {table} ({', '.join(cols)}) "  # noqa: S608
        f"VALUES ({placeholders}) RETURNING *"
    )
    try:
        row = db.execute(sql, body).first()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "validation_failed", "message": str(exc)},
        ) from exc
    obj = dict(row._mapping)
    write_admin_event(
        db,
        user_id=actor_id,
        entity_type=table,
        entity_id=obj["id"],
        action="create",
        after={"id": str(obj["id"])},
    )
    return obj


def update_row(
    db: Session,
    *,
    table: str,
    id_: str,
    payload: dict[str, Any],
    actor_id: uuid.UUID,
    if_match: str | None,
    jsonb_cols: set[str] | None = None,
    forbid_fields: set[str] | None = None,
) -> dict[str, Any]:
    expected = parse_if_match(if_match)
    obj = fetch_one(db, table, id_)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    assert_version_match(expected, int(obj["version"]))
    forbid = forbid_fields or set()
    forbid |= {"id", "status", "version", "created_at", "created_by", "etag"}
    update = {k: v for k, v in payload.items() if k not in forbid and v is not None}
    if not update:
        return obj
    jsonb_cols = jsonb_cols or set()
    for k in jsonb_cols:
        if k in update and update[k] is not None and not isinstance(update[k], str):
            update[k] = json.dumps(update[k], default=_json_default)
    for k, v in list(update.items()):
        if isinstance(v, uuid.UUID):
            update[k] = str(v)
    set_clause = ", ".join(f"{k} = :{k}" for k in update)
    update["id"] = id_
    sql = text(
        f"UPDATE {table} SET {set_clause}, updated_at=now() "  # noqa: S608
        f"WHERE id = CAST(:id AS UUID) RETURNING *"
    )
    try:
        row = db.execute(sql, update).first()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=422,
            detail={"code": "validation_failed", "message": str(exc)},
        ) from exc
    new_obj = dict(row._mapping)
    write_admin_event(
        db,
        user_id=actor_id,
        entity_type=table,
        entity_id=new_obj["id"],
        action="update",
        after={"id": str(new_obj["id"])},
    )
    return new_obj


def publish_row(
    db: Session, *, table: str, id_: str, actor_id: uuid.UUID, if_match: str | None
) -> dict[str, Any]:
    expected = parse_if_match(if_match)
    obj = fetch_one(db, table, id_)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    assert_version_match(expected, int(obj["version"]))
    if obj["status"] == "published":
        raise HTTPException(
            status_code=409,
            detail={"code": "already_published", "message": "Déjà publié."},
        )
    spec: EntitySpec | None = registry.get(table)
    if spec is None:
        raise HTTPException(status_code=500, detail={"code": "spec_missing"})
    verify_sources_or_422(db, spec, obj)
    row = db.execute(
        text(
            f"UPDATE {table} SET status='published', "  # noqa: S608
            f"published_by = CAST(:uid AS UUID), updated_at=now() "
            f"WHERE id = CAST(:id AS UUID) RETURNING *"
        ),
        {"uid": str(actor_id), "id": id_},
    ).first()
    new_obj = dict(row._mapping)
    write_admin_event(
        db,
        user_id=actor_id,
        entity_type=table,
        entity_id=new_obj["id"],
        action="publish",
        after={"id": str(new_obj["id"]), "version": new_obj["version"]},
    )
    return new_obj


def archive_row(
    db: Session, *, table: str, id_: str, actor_id: uuid.UUID, if_match: str | None
) -> dict[str, Any]:
    expected = parse_if_match(if_match)
    obj = fetch_one(db, table, id_)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    assert_version_match(expected, int(obj["version"]))
    row = db.execute(
        text(
            f"UPDATE {table} SET status='archived', updated_at=now() "  # noqa: S608
            f"WHERE id = CAST(:id AS UUID) RETURNING *"
        ),
        {"id": id_},
    ).first()
    new_obj = dict(row._mapping)
    write_admin_event(
        db,
        user_id=actor_id,
        entity_type=table,
        entity_id=new_obj["id"],
        action="archive",
        after={"id": str(new_obj["id"])},
    )
    return new_obj


def _json_default(obj: Any) -> Any:
    if isinstance(obj, uuid.UUID):
        return str(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"not serializable: {type(obj)}")
