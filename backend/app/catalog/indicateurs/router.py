"""F09 US1 — Router ``indicateur`` (admin only)."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, Query, Response
from sqlalchemy.orm import Session

from app.admin.etag import make_etag
from app.auth.dependencies import get_current_admin
from app.catalog.indicateurs import service
from app.catalog.indicateurs.schemas import (
    IndicateurCreate,
    IndicateurUpdate,
    serialize_out,
)
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(prefix="/admin/indicateurs", tags=["admin-indicateurs"])


@router.get("/", summary="Lister les indicateurs")
def list_indicateurs(
    pillar: str | None = Query(None),
    status: str | None = Query(None),
    search: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    page = service.list_indicateurs(
        db,
        pillar=pillar,
        status_filter=status,
        search=search,
        limit=limit,
        offset=offset,
    )
    items = []
    for row in page["items"]:
        sources = service.list_sources(db, str(row["id"]))
        items.append(serialize_out(_to_jsonable(row), sources))
    return {
        "items": items,
        "total": page["total"],
        "limit": page["limit"],
        "offset": page["offset"],
    }


@router.post("/", status_code=201, summary="Créer un indicateur draft")
def create_indicateur(
    payload: IndicateurCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.create_indicateur(db, payload, actor_id=user.id)
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    sources = service.list_sources(db, str(obj["id"]))
    return serialize_out(_to_jsonable(obj), sources)


@router.get("/{id}", summary="Lire un indicateur")
def get_indicateur(
    id: str,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.fetch_one(db, id)
    if not obj:
        from fastapi import HTTPException

        raise HTTPException(status_code=404, detail={"code": "not_found"})
    response.headers["ETag"] = make_etag(obj["version"])
    sources = service.list_sources(db, id)
    return serialize_out(_to_jsonable(obj), sources)


@router.patch("/{id}", summary="Modifier un indicateur")
def patch_indicateur(
    id: str,
    payload: IndicateurUpdate,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.update_indicateur(
        db, id, payload, actor_id=user.id, if_match=if_match
    )
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    sources = service.list_sources(db, str(obj["id"]))
    return serialize_out(_to_jsonable(obj), sources)


@router.post("/{id}/publish", summary="Publier un indicateur draft")
def publish_indicateur(
    id: str,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.publish_indicateur(db, id, actor_id=user.id, if_match=if_match)
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    sources = service.list_sources(db, id)
    return serialize_out(_to_jsonable(obj), sources)


@router.post("/{id}/archive", summary="Archiver un indicateur")
def archive_indicateur(
    id: str,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.archive_indicateur(db, id, actor_id=user.id, if_match=if_match)
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    sources = service.list_sources(db, id)
    return serialize_out(_to_jsonable(obj), sources)


def _to_jsonable(row: dict[str, Any]) -> dict[str, Any]:
    """Convert UUIDs/datetimes to strings for response serialization."""
    import uuid as _uuid

    out: dict[str, Any] = {}
    for k, v in row.items():
        if isinstance(v, _uuid.UUID):
            out[k] = str(v)
        elif hasattr(v, "isoformat"):
            out[k] = v.isoformat()
        else:
            out[k] = v
    return out
