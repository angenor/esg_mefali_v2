"""F08 — Helpers communs aux routers admin Catalog (Fonds, Inter, Acc, Offre).

Encapsule :
- conversion payload Pydantic → params SQL (JSONB sérialisé, UUID[] casté).
- publish gate (réutilise F06 ``verify_sources_or_422``).
- audit log (réutilise F04).
"""

from __future__ import annotations

import json
from typing import Any
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.admin.audit import write_admin_event
from app.admin.etag import assert_version_match, parse_if_match
from app.admin.publish import verify_sources_or_422
from app.admin.registry import EntitySpec

# JSONB columns par entité — sérialisées en JSON string avant bind.
JSONB_COLUMNS: dict[str, set[str]] = {
    "fonds_source": {
        "criteres_json", "documents_requis_json", "frais_json",
        "delais_json", "contact_json", "plafond_money", "plancher_money",
    },
    "intermediaire": {
        "criteres_json", "documents_requis_json", "frais_json",
        "delais_json", "contact_json", "track_record_json",
    },
    "accreditation": {"plafond_money"},
    "offre": {
        "criteres_offre_specifiques", "documents_specifiques",
        "frais_specifiques", "delais_specifiques",
    },
}

# Colonnes UUID[] qui doivent être castées explicitement.
UUID_ARRAY_COLUMNS: set[str] = {"source_ids"}


def serialize_for_sql(table: str, payload: dict[str, Any]) -> dict[str, Any]:
    """Convertit dict Pydantic → params bind SQL.

    - JSONB : json.dumps.
    - UUID[] : list[str] (psycopg gère le cast avec :col).
    - UUID : str.
    - datetime/date : isoformat (psycopg supporte directement aussi).
    """
    jsonb_cols = JSONB_COLUMNS.get(table, set())
    out: dict[str, Any] = {}
    for k, v in payload.items():
        if v is None:
            out[k] = None
        elif k in jsonb_cols:
            out[k] = json.dumps(v, default=_json_default)
        elif k in UUID_ARRAY_COLUMNS:
            out[k] = [str(u) for u in v] if v else []
        elif isinstance(v, UUID):
            out[k] = str(v)
        elif isinstance(v, list) and v and isinstance(v[0], UUID):
            out[k] = [str(x) for x in v]
        else:
            out[k] = v
    return out


def _json_default(obj: Any) -> Any:
    if isinstance(obj, UUID):
        return str(obj)
    if hasattr(obj, "isoformat"):
        return obj.isoformat()
    raise TypeError(f"Type not serializable: {type(obj)}")


def fetch_one(db: Session, table: str, id_: str) -> dict[str, Any] | None:
    row = db.execute(
        text(f"SELECT * FROM {table} WHERE id = CAST(:id AS UUID)"),  # noqa: S608
        {"id": id_},
    ).first()
    return dict(row._mapping) if row else None


def serialize_row(d: dict[str, Any]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, UUID):
            out[k] = str(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        elif isinstance(v, list):
            out[k] = [str(x) if isinstance(x, UUID) else x for x in v]
        else:
            out[k] = v
    return out


def insert_entity(
    db: Session,
    table: str,
    user_id: UUID,
    body: dict[str, Any],
) -> dict[str, Any]:
    """INSERT générique : sérialise JSONB, ajoute draft/version/created_by, audit."""
    body = dict(body)
    body["status"] = "draft"
    body["version"] = 1
    body["created_by"] = str(user_id)
    body = serialize_for_sql(table, body)

    cols = list(body.keys())
    placeholders = []
    for c in cols:
        if c in UUID_ARRAY_COLUMNS:
            placeholders.append(f"CAST(:{c} AS UUID[])")
        else:
            placeholders.append(f":{c}")
    sql = text(
        f"INSERT INTO {table} ({', '.join(cols)}) "  # noqa: S608
        f"VALUES ({', '.join(placeholders)}) RETURNING *"
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
        user_id=user_id,
        entity_type=table,
        entity_id=obj["id"],
        action="create",
        after=serialize_row(obj),
    )
    return obj


def update_entity(
    db: Session,
    table: str,
    user_id: UUID,
    id_: str,
    update_payload: dict[str, Any],
    if_match: str | None,
) -> dict[str, Any]:
    expected = parse_if_match(if_match)
    obj = fetch_one(db, table, id_)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    assert_version_match(expected, int(obj["version"]))

    update_payload = {
        k: v for k, v in update_payload.items()
        if k not in {"status", "version", "id", "created_at", "created_by", "etag"} and v is not None
    }
    if not update_payload:
        return obj
    update_payload = serialize_for_sql(table, update_payload)
    set_parts = []
    for k in update_payload:
        if k in UUID_ARRAY_COLUMNS:
            set_parts.append(f"{k} = CAST(:{k} AS UUID[])")
        else:
            set_parts.append(f"{k} = :{k}")
    set_clause = ", ".join(set_parts)
    update_payload["id"] = id_
    sql = text(
        f"UPDATE {table} SET {set_clause}, updated_at=now() "  # noqa: S608
        f"WHERE id = CAST(:id AS UUID) RETURNING *"
    )
    try:
        new_row = dict(db.execute(sql, update_payload).first()._mapping)
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=422, detail={"code": "validation_failed", "message": str(exc)}
        ) from exc
    write_admin_event(
        db,
        user_id=user_id,
        entity_type=table,
        entity_id=new_row["id"],
        action="update",
        before=serialize_row(obj),
        after=serialize_row(new_row),
    )
    return new_row


def publish_entity(
    db: Session,
    spec: EntitySpec,
    user_id: UUID,
    id_: str,
    if_match: str | None,
) -> dict[str, Any]:
    expected = parse_if_match(if_match)
    obj = fetch_one(db, spec.table, id_)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    assert_version_match(expected, int(obj["version"]))
    if obj["status"] == "published":
        raise HTTPException(
            status_code=409,
            detail={"code": "already_published", "message": "Déjà publié."},
        )
    verify_sources_or_422(db, spec, obj)
    new_row = db.execute(
        text(
            f"UPDATE {spec.table} SET status='published', "  # noqa: S608
            f"published_by = CAST(:uid AS UUID), updated_at=now() "
            f"WHERE id = CAST(:id AS UUID) RETURNING *"
        ),
        {"uid": str(user_id), "id": id_},
    ).first()
    new_obj = dict(new_row._mapping)
    write_admin_event(
        db,
        user_id=user_id,
        entity_type=spec.table,
        entity_id=new_obj["id"],
        action="publish",
        before=serialize_row(obj),
        after=serialize_row(new_obj),
    )
    return new_obj
