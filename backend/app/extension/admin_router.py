"""F33 - Routes admin ``/admin/url-patterns/*``."""

from __future__ import annotations

import logging
import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.db import get_db
from app.extension.schemas import (
    AdminUrlPatternIn,
    AdminUrlPatternListOut,
    AdminUrlPatternOut,
    AdminUrlPatternUpdateIn,
)
from app.extension.service import validate_pattern
from app.models.account_user import AccountUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/admin/url-patterns", tags=["extension-admin"])


def _safe_audit(
    db: Session, *, user_id: uuid.UUID, entity_id: uuid.UUID, action: str
) -> None:
    try:
        from app.audit.helper import record_audit

        record_audit(
            db,
            entity_type="extension",
            entity_id=entity_id,
            field=action,
            new={"action": action},
            source_of_change="manual",
            user_id=user_id,
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001
        logger.warning("admin url-patterns audit failed: %s", exc)
        try:
            db.rollback()
        except Exception:  # pragma: no cover
            pass


def _row_to_out(r: object) -> AdminUrlPatternOut:
    return AdminUrlPatternOut(
        id=r.id,  # type: ignore[attr-defined]
        pattern=r.pattern,  # type: ignore[attr-defined]
        pattern_type=r.pattern_type,  # type: ignore[attr-defined]
        nature=r.nature,  # type: ignore[attr-defined]
        fonds_id=r.fonds_id,  # type: ignore[attr-defined]
        intermediaire_id=r.intermediaire_id,  # type: ignore[attr-defined]
        offre_id=r.offre_id,  # type: ignore[attr-defined]
        is_active=r.is_active,  # type: ignore[attr-defined]
        preferred_language=r.preferred_language,  # type: ignore[attr-defined]
        created_at=r.created_at,  # type: ignore[attr-defined]
        updated_at=r.updated_at,  # type: ignore[attr-defined]
    )


@router.get("", response_model=AdminUrlPatternListOut)
def list_url_patterns(
    limit: int = Query(default=100, ge=1, le=500),
    offset: int = Query(default=0, ge=0),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> AdminUrlPatternListOut:
    total = db.execute(text("SELECT COUNT(*) FROM url_pattern")).scalar() or 0
    rows = db.execute(
        text(
            """
            SELECT id, pattern, pattern_type, nature, fonds_id, intermediaire_id,
                   offre_id, is_active, preferred_language, created_at, updated_at
            FROM url_pattern
            ORDER BY created_at DESC
            LIMIT :lim OFFSET :off
            """
        ),
        {"lim": limit, "off": offset},
    ).all()
    return AdminUrlPatternListOut(
        items=[_row_to_out(r) for r in rows], total=int(total)
    )


@router.post("", response_model=AdminUrlPatternOut, status_code=status.HTTP_201_CREATED)
def create_url_pattern(
    payload: AdminUrlPatternIn,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> AdminUrlPatternOut:
    try:
        validate_pattern(payload.pattern, payload.pattern_type, payload.nature)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "invalid_pattern", "message": str(exc)},
        ) from exc

    now = datetime.now(UTC)
    new_id = uuid.uuid4()
    db.execute(
        text(
            """
            INSERT INTO url_pattern
              (id, pattern, pattern_type, nature, fonds_id, intermediaire_id,
               offre_id, is_active, preferred_language, created_at, updated_at)
            VALUES
              (:id, :pat, :ptype, :nat,
               CAST(:fid AS UUID), CAST(:iid AS UUID), CAST(:oid AS UUID),
               :act, :lang, :cat, :uat)
            """
        ),
        {
            "id": str(new_id),
            "pat": payload.pattern,
            "ptype": payload.pattern_type,
            "nat": payload.nature,
            "fid": str(payload.fonds_id) if payload.fonds_id else None,
            "iid": str(payload.intermediaire_id) if payload.intermediaire_id else None,
            "oid": str(payload.offre_id) if payload.offre_id else None,
            "act": payload.is_active,
            "lang": payload.preferred_language,
            "cat": now,
            "uat": now,
        },
    )
    db.commit()
    _safe_audit(
        db, user_id=user.id, entity_id=new_id, action="extension.admin_pattern_create"
    )
    row = db.execute(
        text(
            """
            SELECT id, pattern, pattern_type, nature, fonds_id, intermediaire_id,
                   offre_id, is_active, preferred_language, created_at, updated_at
            FROM url_pattern WHERE id = CAST(:id AS UUID)
            """
        ),
        {"id": str(new_id)},
    ).first()
    if row is None:
        raise HTTPException(  # pragma: no cover
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "create_failed", "message": "url_pattern create failed"},
        )
    return _row_to_out(row)


@router.patch("/{pattern_id}", response_model=AdminUrlPatternOut)
def update_url_pattern(
    pattern_id: uuid.UUID,
    payload: AdminUrlPatternUpdateIn,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> AdminUrlPatternOut:
    existing = db.execute(
        text(
            """
            SELECT id, pattern, pattern_type, nature, fonds_id, intermediaire_id,
                   offre_id, is_active, preferred_language, created_at, updated_at
            FROM url_pattern WHERE id = CAST(:id AS UUID)
            """
        ),
        {"id": str(pattern_id)},
    ).first()
    if existing is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "url_pattern introuvable"},
        )

    new_pattern = payload.pattern or existing.pattern
    new_ptype = payload.pattern_type or existing.pattern_type
    new_nature = payload.nature or existing.nature
    if payload.pattern is not None or payload.pattern_type is not None:
        try:
            validate_pattern(new_pattern, new_ptype, new_nature)
        except ValueError as exc:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail={"code": "invalid_pattern", "message": str(exc)},
            ) from exc

    now = datetime.now(UTC)
    db.execute(
        text(
            """
            UPDATE url_pattern SET
              pattern = :pat,
              pattern_type = :ptype,
              nature = :nat,
              fonds_id = CAST(:fid AS UUID),
              intermediaire_id = CAST(:iid AS UUID),
              offre_id = CAST(:oid AS UUID),
              is_active = :act,
              preferred_language = :lang,
              updated_at = :uat
            WHERE id = CAST(:id AS UUID)
            """
        ),
        {
            "id": str(pattern_id),
            "pat": new_pattern,
            "ptype": new_ptype,
            "nat": new_nature,
            "fid": str(payload.fonds_id)
            if payload.fonds_id
            else (str(existing.fonds_id) if existing.fonds_id else None),
            "iid": str(payload.intermediaire_id)
            if payload.intermediaire_id
            else (
                str(existing.intermediaire_id) if existing.intermediaire_id else None
            ),
            "oid": str(payload.offre_id)
            if payload.offre_id
            else (str(existing.offre_id) if existing.offre_id else None),
            "act": payload.is_active
            if payload.is_active is not None
            else existing.is_active,
            "lang": payload.preferred_language
            if payload.preferred_language is not None
            else existing.preferred_language,
            "uat": now,
        },
    )
    db.commit()
    _safe_audit(
        db,
        user_id=user.id,
        entity_id=pattern_id,
        action="extension.admin_pattern_update",
    )
    row = db.execute(
        text(
            """
            SELECT id, pattern, pattern_type, nature, fonds_id, intermediaire_id,
                   offre_id, is_active, preferred_language, created_at, updated_at
            FROM url_pattern WHERE id = CAST(:id AS UUID)
            """
        ),
        {"id": str(pattern_id)},
    ).first()
    return _row_to_out(row)


@router.delete("/{pattern_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_url_pattern(
    pattern_id: uuid.UUID,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_admin),
) -> None:
    res = db.execute(
        text(
            "UPDATE url_pattern SET is_active = FALSE, updated_at = now() "
            "WHERE id = CAST(:id AS UUID)"
        ),
        {"id": str(pattern_id)},
    )
    db.commit()
    if res.rowcount == 0:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "url_pattern introuvable"},
        )
    _safe_audit(
        db,
        user_id=user.id,
        entity_id=pattern_id,
        action="extension.admin_pattern_delete",
    )
