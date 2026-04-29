"""F09 US2/US6/US7 — Router ``referentiel``."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.admin.etag import make_etag
from app.auth.dependencies import get_current_admin
from app.catalog._shared import serialize_row
from app.catalog.referentiels import service
from app.catalog.referentiels.schemas import (
    IndicateurAttach,
    ReferentielCreate,
    ReferentielUpdate,
)
from app.catalog.referentiels.validator import validate_for_publish
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(prefix="/admin/referentiels", tags=["admin-referentiels"])


@router.get("/", summary="Lister les référentiels")
def list_referentiels(
    type: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    page = service.list_referentiels(
        db,
        type_=type,
        status_filter=status,
        search=search,
        limit=limit,
        offset=offset,
    )
    items = []
    for row in page["items"]:
        sources = service.list_sources(db, str(row["id"]))
        out = serialize_row(row)
        out["source_ids"] = [str(s) for s in sources]
        items.append(out)
    return {
        "items": items,
        "total": page["total"],
        "limit": page["limit"],
        "offset": page["offset"],
    }


@router.post("/", status_code=201)
def create_referentiel(
    payload: ReferentielCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.create_referentiel(db, payload, actor_id=user.id)
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    out = serialize_row(obj)
    out["source_ids"] = [str(s) for s in service.list_sources(db, str(obj["id"]))]
    return out


@router.get("/{id}")
def get_referentiel(
    id: str,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.fetch_one(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    response.headers["ETag"] = make_etag(obj["version"])
    out = serialize_row(obj)
    out["source_ids"] = [str(s) for s in service.list_sources(db, id)]
    return out


@router.get("/{id}/full", summary="Référentiel + indicateurs liés + sources (FR-003)")
def get_full(
    id: str,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.get_full(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    return serialize_row(obj)


@router.patch("/{id}")
def patch_referentiel(
    id: str,
    payload: ReferentielUpdate,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.update_referentiel(db, id, payload, actor_id=user.id, if_match=if_match)
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    out = serialize_row(obj)
    out["source_ids"] = [str(s) for s in service.list_sources(db, id)]
    return out


@router.post("/{id}/indicateurs", summary="Attacher un indicateur (upsert)")
def attach_indicateur(
    id: str,
    payload: IndicateurAttach,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    if not service.fetch_one(db, id):
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    obj = service.attach_indicateur(db, id, payload, actor_id=user.id)
    db.commit()
    return serialize_row(obj)


@router.delete("/{id}/indicateurs/{indicateur_id}", status_code=204)
def detach_indicateur(
    id: str,
    indicateur_id: str,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> None:
    service.detach_indicateur(db, id, indicateur_id, actor_id=user.id)
    db.commit()


@router.post("/{id}/publish", summary="Publier (validateur FR-005)")
def publish_referentiel(
    id: str,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.publish_referentiel(db, id, actor_id=user.id, if_match=if_match)
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.post("/{id}/validate", summary="Dry-run du validateur de publish")
def validate_referentiel(
    id: str,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    failures = validate_for_publish(db, id)
    return {"failures": failures, "ready": len(failures) == 0}


@router.post("/{id}/archive")
def archive_referentiel(
    id: str,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.archive_referentiel(db, id, actor_id=user.id, if_match=if_match)
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)
