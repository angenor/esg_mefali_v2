"""F09 US3 — Router ``critere`` + endpoint /evaluate."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Body, Depends, Header, HTTPException, Query, Response
from sqlalchemy.orm import Session

from app.admin.etag import make_etag
from app.auth.dependencies import get_current_admin
from app.catalog._shared import serialize_row
from app.catalog.criteres import service
from app.catalog.criteres.dsl import DSLError, evaluate, parse
from app.catalog.criteres.schemas import CritereCreate, CritereUpdate
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(prefix="/admin/criteres", tags=["admin-criteres"])


@router.get("/", summary="Lister les critères")
def list_criteres(
    owner_type: str | None = Query(None),
    owner_id: str | None = Query(None),
    severity: str | None = Query(None),
    status: str | None = Query(None),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    page = service.list_criteres(
        db,
        owner_type=owner_type,
        owner_id=owner_id,
        severity=severity,
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


@router.post("/", status_code=201, summary="Créer un critère draft")
def create_critere(
    payload: CritereCreate,
    response: Response,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.create(db, payload, actor_id=user.id)
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.get("/{id}", summary="Lire un critère")
def get_critere(
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


@router.patch("/{id}", summary="Modifier un critère")
def patch_critere(
    id: str,
    payload: CritereUpdate,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.update(db, id, payload, actor_id=user.id, if_match=if_match)
    db.commit()
    response.headers["ETag"] = make_etag(obj["version"])
    return serialize_row(obj)


@router.post("/{id}/publish", summary="Publier")
def publish_critere(
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


@router.post("/{id}/archive", summary="Archiver")
def archive_critere(
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


@router.post("/{id}/evaluate", summary="Évaluer le DSL contre un contexte fourni")
def evaluate_critere(
    id: str,
    context: dict[str, Any] = Body(...),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    obj = service.get(db, id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    try:
        result = evaluate(obj["expression_json"], context)
    except DSLError as exc:
        raise HTTPException(
            status_code=422, detail={"code": "dsl_error", "message": str(exc)}
        ) from exc
    return {"id": str(obj["id"]), "result": result}


@router.post("/_validate", summary="Valider un payload DSL sans le persister")
def validate_dsl(
    expression: dict[str, Any] = Body(...),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    try:
        parse(expression)
    except DSLError as exc:
        raise HTTPException(
            status_code=422, detail={"code": "dsl_error", "message": str(exc)}
        ) from exc
    return {"valid": True}
