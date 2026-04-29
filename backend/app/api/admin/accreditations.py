"""F08 — Admin router for Accreditations (relation datée Fonds×Inter)."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.admin.etag import make_etag
from app.api.admin._helpers import (
    fetch_one,
    insert_entity,
    serialize_row,
    update_entity,
)
from app.api.admin.specs import register_f08_specs
from app.auth.dependencies import get_current_admin
from app.db import get_db
from app.models.account_user import AccountUser
from app.schemas.accreditation import AccreditationCreate, AccreditationUpdate

register_f08_specs()

router = APIRouter(prefix="/admin/accreditations", tags=["admin-accreditations"])


@router.get("/")
def list_acc(
    fonds_id: str | None = Query(None),
    intermediaire_id: str | None = Query(None),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    where, params = [], {}
    if fonds_id:
        where.append("fonds_id = CAST(:fid AS UUID)")
        params["fid"] = fonds_id
    if intermediaire_id:
        where.append("intermediaire_id = CAST(:iid AS UUID)")
        params["iid"] = intermediaire_id
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""
    rows = db.execute(
        text(
            f"SELECT * FROM accreditation {where_sql} "  # noqa: S608
            f"ORDER BY valid_from DESC, id DESC LIMIT 200"
        ),
        params,
    ).all()
    return {"items": [serialize_row(dict(r._mapping)) for r in rows]}


@router.post("/", status_code=201)
def create_acc(
    payload: AccreditationCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    body = payload.model_dump(mode="json")
    obj = insert_entity(db, "accreditation", user.id, body)
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.get("/{id}")
def get_acc(
    id: str,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = fetch_one(db, "accreditation", id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.put("/{id}")
def put_acc(
    id: str,
    payload: AccreditationUpdate,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    new_obj = update_entity(
        db, "accreditation", user.id, id,
        payload.model_dump(mode="json", exclude_unset=True),
        if_match,
    )
    db.commit()
    response.headers["ETag"] = make_etag(new_obj["version"])
    return serialize_row(new_obj)


@router.get("/{id}/is_active")
def is_active(
    id: str,
    at: str | None = Query(None, description="ISO date ; défaut now()"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = fetch_one(db, "accreditation", id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    at_date = date.fromisoformat(at) if at else None
    vf: date = obj["valid_from"]
    vt: date | None = obj["valid_to"]
    today = at_date or date.today()
    active = (vf <= today) and (vt is None or vt >= today)
    return {"id": id, "active": active, "valid_from": vf.isoformat(),
            "valid_to": vt.isoformat() if vt else None}


def has_active_accreditation(
    db: Session,
    intermediaire_id: str,
    fonds_id: str,
) -> bool:
    """Helper exposé pour Offre — vérifie qu'au moins une accréditation est active."""
    row = db.execute(
        text(
            """
            SELECT 1 FROM accreditation
            WHERE intermediaire_id = CAST(:iid AS UUID)
              AND fonds_id = CAST(:fid AS UUID)
              AND valid_from <= CURRENT_DATE
              AND (valid_to IS NULL OR valid_to >= CURRENT_DATE)
            LIMIT 1
            """
        ),
        {"iid": str(intermediaire_id), "fid": str(fonds_id)},
    ).first()
    return row is not None
