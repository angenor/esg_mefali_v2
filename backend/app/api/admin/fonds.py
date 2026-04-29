"""F08 — Admin router for Fonds source."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.admin.etag import make_etag
from app.admin.registry import registry
from app.api.admin._helpers import (
    fetch_one,
    insert_entity,
    publish_entity,
    serialize_row,
    update_entity,
)
from app.api.admin.specs import register_f08_specs
from app.auth.dependencies import get_current_admin
from app.db import get_db
from app.models.account_user import AccountUser
from app.schemas.fonds_source import FondsCreate, FondsUpdate

register_f08_specs()

router = APIRouter(prefix="/admin/fonds", tags=["admin-fonds"])


@router.get("/", summary="List fonds")
def list_fonds(
    limit: int = Query(50, ge=1, le=200),
    status_filter: str | None = Query(None, alias="status"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    where = []
    params: dict[str, Any] = {"limit": limit}
    if status_filter:
        where.append("status = :st")
        params["st"] = status_filter
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    rows = db.execute(
        text(
            f"SELECT * FROM fonds_source {where_sql} "  # noqa: S608
            f"ORDER BY created_at DESC, id DESC LIMIT :limit"
        ),
        params,
    ).all()
    items = [serialize_row(dict(r._mapping)) for r in rows]
    return {"items": items, "total": len(items)}


@router.post("/", status_code=201, summary="Create fonds (draft)")
def create_fonds(
    payload: FondsCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = insert_entity(db, "fonds_source", user.id, payload.model_dump(mode="json"))
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.get("/{id}", summary="Get fonds by id")
def get_fonds(
    id: str,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = fetch_one(db, "fonds_source", id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.put("/{id}", summary="Update fonds")
def put_fonds(
    id: str,
    payload: FondsUpdate,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    new_obj = update_entity(
        db, "fonds_source", user.id, id,
        payload.model_dump(mode="json", exclude_unset=True),
        if_match,
    )
    db.commit()
    response.headers["ETag"] = make_etag(new_obj["version"])
    return serialize_row(new_obj)


@router.post("/{id}/publish", summary="Publish fonds (≥1 verified source)")
def publish_fonds(
    id: str,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    spec = registry.get("fonds_source")
    if spec is None:
        raise HTTPException(status_code=500, detail={"code": "spec_missing"})
    new_obj = publish_entity(db, spec, user.id, id, if_match)
    db.commit()
    response.headers["ETag"] = make_etag(new_obj["version"])
    return serialize_row(new_obj)


@router.get("/{id}/intermediaires", summary="Intermédiaires accrédités au fonds")
def list_intermediaires_for_fonds(
    id: str,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    rows = db.execute(
        text(
            """
            SELECT DISTINCT i.* FROM intermediaire i
            JOIN accreditation a ON a.intermediaire_id = i.id
            WHERE a.fonds_id = CAST(:fid AS UUID)
              AND a.valid_from <= CURRENT_DATE
              AND (a.valid_to IS NULL OR a.valid_to >= CURRENT_DATE)
            ORDER BY i.name
            """
        ),
        {"fid": id},
    ).all()
    return {"items": [serialize_row(dict(r._mapping)) for r in rows]}
