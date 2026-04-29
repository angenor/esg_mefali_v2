"""F09 US1 — Service ``indicateur`` : CRUD + publish gate + versioning."""

from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.admin.audit import write_admin_event
from app.admin.etag import assert_version_match, parse_if_match
from app.admin.publish import verify_sources_or_422
from app.admin.registry import registry
from app.catalog.indicateurs.schemas import IndicateurCreate, IndicateurUpdate

TABLE = "indicateur"
JUNCTION = "indicateur_source"


def fetch_one(db: Session, id_: str) -> dict[str, Any] | None:
    row = db.execute(
        text(f"SELECT * FROM {TABLE} WHERE id = CAST(:id AS UUID)"),  # noqa: S608
        {"id": id_},
    ).first()
    return dict(row._mapping) if row else None


def list_sources(db: Session, indicateur_id: str) -> list[uuid.UUID]:
    rows = db.execute(
        text(
            f"SELECT source_id FROM {JUNCTION} "  # noqa: S608
            "WHERE indicateur_id = CAST(:id AS UUID)"
        ),
        {"id": indicateur_id},
    ).all()
    return [r[0] for r in rows]


def _set_sources(
    db: Session, indicateur_id: str, source_ids: list[uuid.UUID]
) -> None:
    db.execute(
        text(f"DELETE FROM {JUNCTION} WHERE indicateur_id = CAST(:id AS UUID)"),  # noqa: S608
        {"id": indicateur_id},
    )
    for sid in source_ids:
        db.execute(
            text(
                f"INSERT INTO {JUNCTION}(indicateur_id, source_id) "  # noqa: S608
                "VALUES (CAST(:i AS UUID), CAST(:s AS UUID))"
            ),
            {"i": indicateur_id, "s": str(sid)},
        )


def create_indicateur(
    db: Session, payload: IndicateurCreate, *, actor_id: uuid.UUID
) -> dict[str, Any]:
    body: dict[str, Any] = {
        "code": payload.code,
        "name": payload.name,
        "definition": payload.definition,
        "pillar": payload.pillar,
        "unite": payload.unite,
        "value_type": payload.value_type,
        "enum_values": payload.enum_values,
        "status": "draft",
        "version": 1,
        "created_by": str(actor_id),
    }
    import json

    if body["enum_values"] is not None:
        body["enum_values"] = json.dumps(body["enum_values"])

    cols = list(body.keys())
    placeholders = ", ".join(f":{c}" for c in cols)
    sql = text(
        f"INSERT INTO {TABLE} ({', '.join(cols)}) "  # noqa: S608
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
    if payload.source_ids:
        _set_sources(db, str(obj["id"]), payload.source_ids)
    write_admin_event(
        db,
        user_id=actor_id,
        entity_type=TABLE,
        entity_id=obj["id"],
        action="create",
        after={"id": str(obj["id"]), "code": obj["code"]},
    )
    return obj


def update_indicateur(
    db: Session,
    id_: str,
    payload: IndicateurUpdate,
    *,
    actor_id: uuid.UUID,
    if_match: str | None,
) -> dict[str, Any]:
    expected = parse_if_match(if_match)
    obj = fetch_one(db, id_)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    assert_version_match(expected, int(obj["version"]))

    if obj["status"] == "published":
        # publish_new_version : copy → v(N+1) draft. Here in-place new version row.
        return _new_version_from(db, obj, payload, actor_id=actor_id)

    update_payload: dict[str, Any] = {}
    for k in ("name", "definition", "pillar", "unite", "value_type", "enum_values"):
        v = getattr(payload, k)
        if v is not None:
            update_payload[k] = v
    if "enum_values" in update_payload and update_payload["enum_values"] is not None:
        import json

        update_payload["enum_values"] = json.dumps(update_payload["enum_values"])

    if update_payload:
        set_clause = ", ".join(f"{k} = :{k}" for k in update_payload)
        update_payload["id"] = id_
        sql = text(
            f"UPDATE {TABLE} SET {set_clause}, updated_at=now() "  # noqa: S608
            f"WHERE id = CAST(:id AS UUID) RETURNING *"
        )
        try:
            row = db.execute(sql, update_payload).first()
        except Exception as exc:  # noqa: BLE001
            db.rollback()
            raise HTTPException(
                status_code=422,
                detail={"code": "validation_failed", "message": str(exc)},
            ) from exc
        obj = dict(row._mapping)
    if payload.source_ids is not None:
        _set_sources(db, id_, payload.source_ids)
    write_admin_event(
        db,
        user_id=actor_id,
        entity_type=TABLE,
        entity_id=obj["id"],
        action="update",
        after={"id": str(obj["id"])},
    )
    return obj


def _new_version_from(
    db: Session,
    current: dict[str, Any],
    payload: IndicateurUpdate,
    *,
    actor_id: uuid.UUID,
) -> dict[str, Any]:
    """Promote ``current`` (published) → outdated, insert a v(N+1) draft.

    Mirrors crud_router behaviour but for indicateur (with junction sources copied).
    """
    import json

    current_id = str(current["id"])
    db.execute(
        text(
            f"UPDATE {TABLE} SET status='outdated', valid_to=now(), updated_at=now() "  # noqa: S608
            f"WHERE id = CAST(:id AS UUID)"
        ),
        {"id": current_id},
    )
    new = dict(current)
    new.pop("id")
    new["status"] = "draft"
    new["version"] = int(current["version"]) + 1
    new["parent_id"] = current_id
    new["valid_to"] = None
    # New row gets fresh timestamps.
    for k in ("created_at", "updated_at", "valid_from"):
        new.pop(k, None)
    new["published_by"] = None
    # apply patch
    for k in ("name", "definition", "pillar", "unite", "value_type", "enum_values"):
        v = getattr(payload, k)
        if v is not None:
            new[k] = v
    if isinstance(new.get("enum_values"), list):
        new["enum_values"] = json.dumps(new["enum_values"])
    cols = list(new.keys())
    placeholders = ", ".join(f":{c}" for c in cols)
    params = {c: (str(v) if isinstance(v, uuid.UUID) else v) for c, v in new.items()}
    sql = text(
        f"INSERT INTO {TABLE} ({', '.join(cols)}, valid_from, created_at, updated_at) "  # noqa: S608
        f"VALUES ({placeholders}, now(), now(), now()) RETURNING *"
    )
    row = db.execute(sql, params).first()
    new_obj = dict(row._mapping)
    new_id = str(new_obj["id"])
    # Carry over sources from previous version unless overridden.
    if payload.source_ids is not None:
        _set_sources(db, new_id, payload.source_ids)
    else:
        prev_sources = list_sources(db, current_id)
        _set_sources(db, new_id, prev_sources)
    write_admin_event(
        db,
        user_id=actor_id,
        entity_type=TABLE,
        entity_id=new_obj["id"],
        action="new_version",
        before={"id": current_id, "version": current["version"]},
        after={"id": new_id, "version": new_obj["version"]},
    )
    return new_obj


def publish_indicateur(
    db: Session, id_: str, *, actor_id: uuid.UUID, if_match: str | None
) -> dict[str, Any]:
    expected = parse_if_match(if_match)
    obj = fetch_one(db, id_)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    assert_version_match(expected, int(obj["version"]))
    if obj["status"] == "published":
        raise HTTPException(
            status_code=409,
            detail={"code": "already_published", "message": "Déjà publié."},
        )
    sources = list_sources(db, id_)
    if not sources:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "sources_not_verified",
                "missing_sources": [],
                "message": "Aucune source liée — publication impossible.",
            },
        )
    spec = registry.get(TABLE)
    obj["_source_ids"] = [str(s) for s in sources]
    verify_sources_or_422(db, spec, obj)
    row = db.execute(
        text(
            f"UPDATE {TABLE} SET status='published', "  # noqa: S608
            f"published_by = CAST(:uid AS UUID), updated_at=now() "
            f"WHERE id = CAST(:id AS UUID) RETURNING *"
        ),
        {"uid": str(actor_id), "id": id_},
    ).first()
    new_obj = dict(row._mapping)
    write_admin_event(
        db,
        user_id=actor_id,
        entity_type=TABLE,
        entity_id=new_obj["id"],
        action="publish",
        after={"id": str(new_obj["id"]), "version": new_obj["version"]},
    )
    return new_obj


def archive_indicateur(
    db: Session, id_: str, *, actor_id: uuid.UUID, if_match: str | None
) -> dict[str, Any]:
    expected = parse_if_match(if_match)
    obj = fetch_one(db, id_)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    assert_version_match(expected, int(obj["version"]))
    row = db.execute(
        text(
            f"UPDATE {TABLE} SET status='archived', updated_at=now() "  # noqa: S608
            f"WHERE id = CAST(:id AS UUID) RETURNING *"
        ),
        {"id": id_},
    ).first()
    new_obj = dict(row._mapping)
    write_admin_event(
        db,
        user_id=actor_id,
        entity_type=TABLE,
        entity_id=new_obj["id"],
        action="archive",
        after={"id": str(new_obj["id"])},
    )
    return new_obj


def list_indicateurs(
    db: Session,
    *,
    pillar: str | None = None,
    status_filter: str | None = None,
    search: str | None = None,
    limit: int = 50,
    offset: int = 0,
) -> dict[str, Any]:
    where: list[str] = []
    params: dict[str, Any] = {"limit": limit, "offset": offset}
    if pillar:
        where.append("pillar = :pillar")
        params["pillar"] = pillar
    if status_filter:
        where.append("status = :status")
        params["status"] = status_filter
    if search:
        where.append("(code ILIKE :q OR name ILIKE :q)")
        params["q"] = f"%{search}%"
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    sql = text(
        f"SELECT * FROM {TABLE} {where_sql} "  # noqa: S608
        f"ORDER BY created_at DESC, id DESC "
        f"LIMIT :limit OFFSET :offset"
    )
    rows = [dict(r._mapping) for r in db.execute(sql, params).all()]
    total = db.execute(
        text(f"SELECT count(*) FROM {TABLE} {where_sql}"),  # noqa: S608
        {k: v for k, v in params.items() if k not in {"limit", "offset"}},
    ).scalar() or 0
    return {"items": rows, "total": int(total), "limit": limit, "offset": offset}
