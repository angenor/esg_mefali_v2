"""F06 US2 — Publish workflow router.

POST /admin/{entity}/{id}/publish:
  - Vérifie If-Match (412 sinon).
  - Vérifie que toutes les sources liées ont ``verification_status='verified'``.
  - Sinon : 422 avec ``missing_sources`` détaillé.
  - Sinon : status='published', published_by=user, audit append.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, Header, HTTPException, Response, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.admin.audit import write_admin_event
from app.admin.crud_router import _fetch_one, _get_spec_or_404, _serialize
from app.admin.etag import assert_version_match, make_etag, parse_if_match
from app.admin.registry import EntitySpec
from app.auth.dependencies import get_current_admin
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(prefix="/admin", tags=["admin-publish"])


def verify_sources_or_422(
    db: Session, spec: EntitySpec, instance: dict[str, Any]
) -> None:
    """Raise 422 if any related source is not in ``verified`` state.

    Pure helper exposed for unit tests (T027).
    """
    if spec.sources_relation is None:
        return
    source_ids = [str(s) for s in spec.sources_relation(instance) if s]
    if not source_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "sources_not_verified",
                "missing_sources": [],
                "message": "Aucune source liée — publication impossible.",
            },
        )
    rows = db.execute(
        text(
            "SELECT id, verification_status, title FROM source "
            "WHERE id = ANY(CAST(:ids AS UUID[]))"
        ),
        {"ids": source_ids},
    ).all()
    found = {str(r._mapping["id"]): r._mapping for r in rows}
    missing: list[dict[str, Any]] = []
    for sid in source_ids:
        meta = found.get(sid)
        if not meta:
            missing.append({"id": sid, "status": "unknown", "label": "(introuvable)"})
            continue
        if meta["verification_status"] != "verified":
            missing.append(
                {
                    "id": sid,
                    "status": meta["verification_status"],
                    "label": meta["title"] or "(sans titre)",
                }
            )
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={
                "code": "sources_not_verified",
                "missing_sources": missing,
                "message": f"{len(missing)} source(s) non verified.",
            },
        )


@router.post("/{entity}/{id}/publish", summary="Publish a draft")
def publish(
    entity: str,
    id: str,
    response: Response,
    if_match: str | None = Header(None, alias="If-Match"),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> dict[str, Any]:
    spec = _get_spec_or_404(entity)
    expected = parse_if_match(if_match)

    obj = _fetch_one(db, spec, id)
    if not obj:
        raise HTTPException(status_code=404, detail={"code": "not_found"})
    assert_version_match(expected, int(obj[spec.version_column]))
    if obj[spec.status_column] == "published":
        raise HTTPException(
            status_code=409,
            detail={"code": "already_published", "message": "Déjà publié."},
        )

    verify_sources_or_422(db, spec, obj)

    new_row = db.execute(
        text(
            f"UPDATE {spec.table} SET status='published', published_by = CAST(:uid AS UUID), "  # noqa: S608
            f"updated_at=now() WHERE {spec.pk_column} = CAST(:id AS UUID) RETURNING *"
        ),
        {"uid": str(user.id), "id": id},
    ).first()
    new_obj = dict(new_row._mapping)
    write_admin_event(
        db,
        user_id=user.id,
        entity_type=spec.name,
        entity_id=new_obj[spec.pk_column],
        action="publish",
        before=_serialize(obj),
        after=_serialize(new_obj),
    )
    db.commit()
    response.headers["ETag"] = make_etag(new_obj[spec.version_column])
    return _serialize(new_obj)
