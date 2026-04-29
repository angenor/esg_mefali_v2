"""F08 — Admin router for Intermédiaires."""

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
from app.schemas.intermediaire import IntermediaireCreate, IntermediaireUpdate

register_f08_specs()

router = APIRouter(prefix="/admin/intermediaires", tags=["admin-intermediaires"])


@router.get("/", summary="List intermédiaires")
def list_inter(
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
            f"SELECT * FROM intermediaire {where_sql} "  # noqa: S608
            f"ORDER BY created_at DESC, id DESC LIMIT :limit"
        ),
        params,
    ).all()
    items = [serialize_row(dict(r._mapping)) for r in rows]
    return {"items": items, "total": len(items)}


@router.post("/", status_code=201)
def create_inter(
    payload: IntermediaireCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = insert_entity(db, "intermediaire", user.id, payload.model_dump(mode="json"))
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.get("/{id}")
def get_inter(
    id: str,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = fetch_one(db, "intermediaire", id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.put("/{id}")
def put_inter(
    id: str,
    payload: IntermediaireUpdate,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    new_obj = update_entity(
        db, "intermediaire", user.id, id,
        payload.model_dump(mode="json", exclude_unset=True),
        if_match,
    )
    db.commit()
    response.headers["ETag"] = make_etag(new_obj["version"])
    return serialize_row(new_obj)


@router.post("/{id}/publish")
def publish_inter(
    id: str,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    spec = registry.get("intermediaire")
    if spec is None:
        raise HTTPException(status_code=500, detail={"code": "spec_missing"})
    new_obj = publish_entity(db, spec, user.id, id, if_match)
    db.commit()
    response.headers["ETag"] = make_etag(new_obj["version"])
    return serialize_row(new_obj)


@router.get("/{id}/fonds", summary="Fonds pour lesquels l'inter est accrédité")
def list_fonds_for_inter(
    id: str,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    rows = db.execute(
        text(
            """
            SELECT DISTINCT f.* FROM fonds_source f
            JOIN accreditation a ON a.fonds_id = f.id
            WHERE a.intermediaire_id = CAST(:iid AS UUID)
              AND a.valid_from <= CURRENT_DATE
              AND (a.valid_to IS NULL OR a.valid_to >= CURRENT_DATE)
            ORDER BY f.name
            """
        ),
        {"iid": id},
    ).all()
    return {"items": [serialize_row(dict(r._mapping)) for r in rows]}
