"""F33 - Routes PME ``/extension/*``."""

from __future__ import annotations

import logging
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.db import get_db
from app.extension.schemas import (
    FieldMappingListOut,
    ProfileSummaryOut,
    SuggestFieldIn,
    SuggestFieldOut,
    UrlPatternListOut,
)
from app.extension.service import (
    build_profile_summary,
    list_active_url_patterns,
    list_field_mappings,
    suggest_field,
)
from app.models.account_user import AccountUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/extension", tags=["extension"])


def _safe_audit(
    db: Session,
    *,
    account_id: uuid.UUID | None,
    user_id: uuid.UUID,
    action: str,
    notes: str | None = None,
) -> None:
    try:
        from app.audit.helper import record_audit

        record_audit(
            db,
            entity_type="extension",
            entity_id=account_id or user_id,
            field=action,
            new={"action": action, "notes": notes} if notes else {"action": action},
            source_of_change="manual",
            user_id=user_id,
            account_id=account_id,
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001 - audit best-effort
        logger.warning("extension: audit failed for action=%s: %s", action, exc)
        try:
            db.rollback()
        except Exception:  # pragma: no cover
            pass


@router.get("/url-patterns", response_model=UrlPatternListOut)
def get_url_patterns(
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> UrlPatternListOut:
    out = list_active_url_patterns(db)
    _safe_audit(
        db,
        account_id=user.account_id,
        user_id=user.id,
        action="extension.view_patterns",
    )
    return out


@router.get("/profile-summary", response_model=ProfileSummaryOut)
def get_profile_summary(
    projet_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> ProfileSummaryOut:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "PME sans account_id."},
        )
    out = build_profile_summary(db, account_id=user.account_id, projet_id=projet_id)
    _safe_audit(
        db,
        account_id=user.account_id,
        user_id=user.id,
        action="extension.profile_summary",
    )
    return out


@router.post("/suggest-field", response_model=SuggestFieldOut)
def post_suggest_field(
    payload: SuggestFieldIn,
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> SuggestFieldOut:
    out = suggest_field(db, payload=payload)
    _safe_audit(
        db,
        account_id=user.account_id,
        user_id=user.id,
        action="extension.suggest_field",
        notes=f"label={payload.field_label[:80]}|src={out.source}",
    )
    return out


@router.get("/field-mappings", response_model=FieldMappingListOut)
def get_field_mappings(
    intermediaire_id: uuid.UUID | None = Query(default=None),
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> FieldMappingListOut:
    out = list_field_mappings(db, intermediaire_id=intermediaire_id)
    _safe_audit(
        db,
        account_id=user.account_id,
        user_id=user.id,
        action="extension.field_mappings",
    )
    return out
