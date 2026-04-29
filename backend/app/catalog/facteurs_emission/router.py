"""F09 US5 — Router ``facteur_emission``."""

from __future__ import annotations

from datetime import date
from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.admin.etag import make_etag
from app.auth.dependencies import get_current_admin
from app.catalog._shared import serialize_row
from app.catalog.facteurs_emission import service
from app.catalog.facteurs_emission.lookup import get_facteur
from app.catalog.facteurs_emission.schemas import (
    FacteurEmissionCreate,
    FacteurEmissionUpdate,
)
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(prefix="/admin/facteurs-emission", tags=["admin-facteurs-emission"])


@router.get("/lookup", summary="Helper lookup (FR-007)")
def lookup_facteur(
    code: str,
    pays_iso2: str | None = Query(None),
    at: date | None = Query(None),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = get_facteur(db, code, pays_iso2=pays_iso2, at=at)
    if not obj:
        raise HTTPException(
            status_code=404,
            detail={"code": "facteur_not_found", "message": "Aucun facteur disponible."},
        )
    return serialize_row(obj)


@router.get("/", summary="Lister les facteurs d'émission")
def list_facteurs(
    code: str | None = Query(None),
    pays_iso2: str | None = Query(None),
    scope: str | None = Query(None),
    categorie: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    page = service.list_facteurs(
        db,
        code=code,
        pays_iso2=pays_iso2,
        scope=scope,
        categorie=categorie,
        status_filter=status,
        limit=limit,
        offset=offset,
    )
    return {
        "items": [serialize_row(r) for r in page["items"]],
        "total": page["total"],
        "limit": page["limit"],
        "offset": page["offset"],
    }


@router.post("/", status_code=201)
def create_facteur(
    payload: FacteurEmissionCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.create(db, payload, actor_id=user.id)
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.get("/{id}")
def get_facteur_route(
    id: str,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.patch("/{id}")
def patch_facteur(
    id: str,
    payload: FacteurEmissionUpdate,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.update(db, id, payload, actor_id=user.id, if_match=if_match)
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.post("/{id}/publish")
def publish_facteur(
    id: str,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.publish(db, id, actor_id=user.id, if_match=if_match)
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.post("/{id}/archive")
def archive_facteur(
    id: str,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.archive(db, id, actor_id=user.id, if_match=if_match)
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)
