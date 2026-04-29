"""F08 — Admin router for Offres (Fonds × Intermediaire)."""

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
from app.api.admin.accreditations import has_active_accreditation
from app.api.admin.specs import register_f08_specs
from app.auth.dependencies import get_current_admin
from app.core.effective_calculator import compute_effective
from app.db import get_db
from app.models.account_user import AccountUser
from app.schemas.offre import OffreCreate, OffreUpdate

register_f08_specs()

router = APIRouter(prefix="/admin/offres", tags=["admin-offres"])


def _ensure_active_accreditation(db: Session, fonds_id: str, intermediaire_id: str) -> None:
    if not has_active_accreditation(db, intermediaire_id, fonds_id):
        raise HTTPException(
            status_code=409,
            detail={
                "code": "no_active_accreditation",
                "message": "Aucune accréditation active entre cet intermédiaire et ce fonds.",
            },
        )


@router.get("/")
def list_offres(
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
            f"SELECT * FROM offre {where_sql} "  # noqa: S608
            f"ORDER BY created_at DESC, id DESC LIMIT :limit"
        ),
        params,
    ).all()
    return {"items": [serialize_row(dict(r._mapping)) for r in rows]}


@router.post("/", status_code=201)
def create_offre(
    payload: OffreCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    body = payload.model_dump(mode="json")
    _ensure_active_accreditation(db, body["fonds_id"], body["intermediaire_id"])
    try:
        obj = insert_entity(db, "offre", user.id, body)
    except HTTPException as exc:
        # Duplicate triggers UNIQUE constraint → 409.
        msg = str(exc.detail.get("message", "")) if isinstance(exc.detail, dict) else ""
        if "uq_offre_fonds_inter_name" in msg or "duplicate key" in msg.lower():
            raise HTTPException(
                status_code=409,
                detail={"code": "duplicate_offre", "message": "Couple (fonds, inter, name) déjà présent."},
            ) from exc
        raise
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.get("/{id}")
def get_offre(
    id: str,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = fetch_one(db, "offre", id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.put("/{id}")
def put_offre(
    id: str,
    payload: OffreUpdate,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    new_obj = update_entity(
        db, "offre", user.id, id,
        payload.model_dump(mode="json", exclude_unset=True),
        if_match,
    )
    db.commit()
    response.headers["ETag"] = make_etag(new_obj["version"])
    return serialize_row(new_obj)


@router.post("/{id}/publish")
def publish_offre(
    id: str,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    spec = registry.get("offre")
    if spec is None:
        raise HTTPException(status_code=500, detail={"code": "spec_missing"})
    obj = fetch_one(db, "offre", id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    _ensure_active_accreditation(db, str(obj["fonds_id"]), str(obj["intermediaire_id"]))
    new_obj = publish_entity(db, spec, user.id, id, if_match)
    db.commit()
    response.headers["ETag"] = make_etag(new_obj["version"])
    return serialize_row(new_obj)


@router.get("/{id}/effective", summary="Calcul effective (Fonds + Inter + Offre)")
def get_effective(
    id: str,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    offre = fetch_one(db, "offre", id)
    if not offre:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    fonds = fetch_one(db, "fonds_source", str(offre["fonds_id"]))
    inter = fetch_one(db, "intermediaire", str(offre["intermediaire_id"]))
    if not fonds or not inter:
        raise HTTPException(status_code=409, detail={"code": "incomplete_offre"})
    eff = compute_effective(fonds, inter, offre)
    return serialize_row(eff)
