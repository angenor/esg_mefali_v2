"""F06 — Generic CRUD router driven by ``EntityRegistry``.

Operates at the SQL level via ``text()`` (no ORM dependency on the entity)
so any registered table can be exposed without writing per-entity routes.

Endpoints:
- GET    /admin/{entity}/         — list (cursor pagination + status filter)
- POST   /admin/{entity}/         — create draft
- GET    /admin/{entity}/{id}     — read one (ETag header)
- PUT    /admin/{entity}/{id}     — update (If-Match required ; published → new version)
- GET    /admin/{entity}/{id}/versions — version history
"""

from __future__ import annotations

from typing import Any
from uuid import UUID

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.admin.audit import write_admin_event
from app.admin.etag import assert_version_match, make_etag, parse_if_match
from app.admin.pagination import build_page, decode_cursor
from app.admin.registry import EntitySpec, registry
from app.auth.dependencies import get_current_admin
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(prefix="/admin", tags=["admin-crud"])


_ALLOWED_STATUS = {"draft", "published", "outdated", "pending"}


def _row_to_dict(row: Any) -> dict[str, Any]:
    return dict(row._mapping) if hasattr(row, "_mapping") else dict(row)


def _serialize(d: dict[str, Any]) -> dict[str, Any]:
    """Render UUIDs/datetimes as strings for JSON payload."""
    out: dict[str, Any] = {}
    for k, v in d.items():
        if isinstance(v, UUID):
            out[k] = str(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out


def _get_spec_or_404(entity: str) -> EntitySpec:
    spec = registry.get(entity)
    if spec is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "unknown_entity", "message": f"Entité inconnue: {entity}"},
        )
    return spec


def _fetch_one(db: Session, spec: EntitySpec, id_: str) -> dict[str, Any] | None:
    row = db.execute(
        text(f"SELECT * FROM {spec.table} WHERE {spec.pk_column} = CAST(:id AS UUID)"),  # noqa: S608
        {"id": id_},
    ).first()
    return _row_to_dict(row) if row else None


@router.get("/{entity}/", summary="List paginated")
def list_entities(
    entity: str,
    request: Request,
    response: Response,
    limit: int = Query(50, ge=1, le=200),
    cursor: str | None = Query(None),
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    spec = _get_spec_or_404(entity)
    if status_filter and status_filter not in _ALLOWED_STATUS:
        raise HTTPException(status_code=400, detail={"code": "invalid_status"})

    decoded = decode_cursor(cursor)
    where_clauses: list[str] = []
    params: dict[str, Any] = {"limit": limit + 1}
    if status_filter:
        where_clauses.append(f"{spec.status_column} = :st")
        params["st"] = status_filter
    if decoded:
        where_clauses.append(
            f"({spec.created_at_column}, {spec.pk_column}) < (:ck, CAST(:cid AS UUID))"
        )
        params["ck"] = decoded["created_at"]
        params["cid"] = decoded["id"]

    where_sql = ("WHERE " + " AND ".join(where_clauses)) if where_clauses else ""
    sql = text(
        f"""
        SELECT * FROM {spec.table}
        {where_sql}
        ORDER BY {spec.created_at_column} DESC, {spec.pk_column} DESC
        LIMIT :limit
        """  # noqa: S608
    )
    rows = [_row_to_dict(r) for r in db.execute(sql, params).all()]

    # Estimate total via pg_class.reltuples (cheap).
    est = db.execute(
        text("SELECT reltuples::BIGINT AS est FROM pg_class WHERE relname = :n"),
        {"n": spec.table},
    ).scalar() or 0
    page = build_page(rows, limit, total_estimate=int(est))
    page["items"] = [_serialize(it) for it in page["items"]]
    return page


@router.post("/{entity}/", status_code=201, summary="Create draft")
def create_entity(
    entity: str,
    payload: dict[str, Any],
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    spec = _get_spec_or_404(entity)
    body = dict(payload)
    body["status"] = "draft"
    body["version"] = 1
    body["created_by"] = str(user.id)

    cols = list(body.keys())
    placeholders = ", ".join(f":{c}" for c in cols)
    sql = text(
        f"INSERT INTO {spec.table} ({', '.join(cols)}) VALUES ({placeholders}) RETURNING *"  # noqa: S608
    )
    try:
        row = db.execute(sql, body).first()
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "validation_failed", "message": str(exc)},
        ) from exc
    obj = _row_to_dict(row)
    write_admin_event(
        db,
        user_id=user.id,
        entity_type=spec.name,
        entity_id=obj[spec.pk_column],
        action="create",
        after=_serialize(obj),
    )
    db.commit()
    response.headers["ETag"] = make_etag(obj.get(spec.version_column, 1))
    return _serialize(obj)


@router.get("/{entity}/{id}", summary="Read one")
def get_entity(
    entity: str,
    id: str,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    spec = _get_spec_or_404(entity)
    obj = _fetch_one(db, spec, id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    response.headers["ETag"] = make_etag(obj.get(spec.version_column, 1))
    return _serialize(obj)


@router.put("/{entity}/{id}", summary="Update (draft or new version)")
def update_entity(
    entity: str,
    id: str,
    payload: dict[str, Any],
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    spec = _get_spec_or_404(entity)
    expected_version = parse_if_match(if_match)

    obj = _fetch_one(db, spec, id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    current_version = int(obj[spec.version_column])
    assert_version_match(expected_version, current_version)

    # Disallow status mutation through PUT (workflow gates only).
    update_payload = {k: v for k, v in payload.items() if k not in {"status", "version", "id", "created_at", "created_by"}}

    if obj[spec.status_column] == "published":
        # Trigger new version: mark current as outdated, insert new draft.
        db.execute(
            text(
                f"UPDATE {spec.table} SET status='outdated', valid_to=now(), updated_at=now() "  # noqa: S608
                f"WHERE {spec.pk_column} = CAST(:id AS UUID)"
            ),
            {"id": id},
        )
        new_payload = {**obj, **update_payload}
        new_payload.pop(spec.pk_column, None)
        new_payload["status"] = "draft"
        new_payload["version"] = current_version + 1
        new_payload["parent_id"] = obj[spec.pk_column]
        new_payload["valid_from"] = "now()"  # marker, replaced below
        new_payload["valid_to"] = None
        new_payload["created_at"] = "now()"
        new_payload["updated_at"] = "now()"
        new_payload["published_by"] = None
        # Build SQL using server defaults for timestamp markers.
        cols = [c for c in new_payload if c not in {"valid_from", "created_at", "updated_at"}]
        placeholders = ", ".join(f":{c}" for c in cols)
        sql = text(
            f"INSERT INTO {spec.table} ({', '.join(cols)}, valid_from, created_at, updated_at) "  # noqa: S608
            f"VALUES ({placeholders}, now(), now(), now()) RETURNING *"
        )
        params = {c: new_payload[c] for c in cols}
        # ensure UUIDs serialised as str
        for k, v in list(params.items()):
            if isinstance(v, UUID):
                params[k] = str(v)
        new_row = _row_to_dict(db.execute(sql, params).first())
        write_admin_event(
            db,
            user_id=user.id,
            entity_type=spec.name,
            entity_id=new_row[spec.pk_column],
            action="new_version",
            before=_serialize(obj),
            after=_serialize(new_row),
        )
        db.commit()
        response.headers["ETag"] = make_etag(new_row[spec.version_column])
        return _serialize(new_row)

    # status == 'draft' (or pending): in-place update, no version bump.
    if not update_payload:
        response.headers["ETag"] = make_etag(current_version)
        return _serialize(obj)
    set_clause = ", ".join(f"{k} = :{k}" for k in update_payload)
    update_payload["id"] = id
    sql = text(
        f"UPDATE {spec.table} SET {set_clause}, updated_at=now() "  # noqa: S608
        f"WHERE {spec.pk_column} = CAST(:id AS UUID) RETURNING *"
    )
    try:
        new_row = _row_to_dict(db.execute(sql, update_payload).first())
    except Exception as exc:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=422, detail={"code": "validation_failed", "message": str(exc)}
        ) from exc
    write_admin_event(
        db,
        user_id=user.id,
        entity_type=spec.name,
        entity_id=new_row[spec.pk_column],
        action="update",
        before=_serialize(obj),
        after=_serialize(new_row),
    )
    db.commit()
    response.headers["ETag"] = make_etag(new_row[spec.version_column])
    return _serialize(new_row)


@router.get("/{entity}/{id}/versions", summary="List versions")
def list_versions(
    entity: str,
    id: str,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    spec = _get_spec_or_404(entity)
    obj = _fetch_one(db, spec, id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    logical = obj.get("logical_id") or obj[spec.pk_column]
    rows = db.execute(
        text(
            f"SELECT {spec.pk_column} AS id, {spec.version_column} AS version, "  # noqa: S608
            f"valid_from, valid_to, {spec.status_column} AS status, published_by "
            f"FROM {spec.table} WHERE logical_id = CAST(:lid AS UUID) "
            f"ORDER BY {spec.version_column} DESC"
        ),
        {"lid": str(logical)},
    ).all()
    return {"items": [_serialize(_row_to_dict(r)) for r in rows]}
