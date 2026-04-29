"""F09 US4 — Router ``document_requis``."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.admin.etag import make_etag
from app.auth.dependencies import get_current_admin
from app.catalog._shared import serialize_row
from app.catalog.documents_requis import service
from app.catalog.documents_requis.schemas import (
    DocumentRequisCreate,
    DocumentRequisUpdate,
)
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(prefix="/admin/documents-requis", tags=["admin-documents-requis"])


@router.get("/", summary="Lister les documents requis")
def list_documents(
    owner_type: str | None = Query(None),
    owner_id: str | None = Query(None),
    type: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    page = service.list_documents(
        db,
        owner_type=owner_type,
        owner_id=owner_id,
        type_=type,
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
def create_document(
    payload: DocumentRequisCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.create(db, payload, actor_id=user.id)
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.get("/{id}")
def get_document(
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
def patch_document(
    id: str,
    payload: DocumentRequisUpdate,
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
def publish_document(
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
def archive_document(
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
