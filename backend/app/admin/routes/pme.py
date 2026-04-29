"""F10 US1 — Admin PME routes (read-only)."""

from __future__ import annotations

from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.admin.deps import require_admin
from app.admin.services import pme_view
from app.audit.admin_view import AdminViewSection
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(prefix="/admin/pme", tags=["admin-pme"])


@router.get("")
def list_pme(
    q: str | None = Query(default=None, max_length=200),
    limit: int = Query(default=25, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    admin: AccountUser = Depends(require_admin),  # noqa: ARG001
    db: Session = Depends(get_db),
) -> dict:
    """List PME accounts with optional name/email search."""
    return pme_view.list_accounts(db, q=q, limit=limit, offset=offset)


@router.get("/{account_id}")
def get_pme_detail(
    account_id: UUID,
    request: Request,
    section: AdminViewSection = Query(default=AdminViewSection.OVERVIEW),
    admin: AccountUser = Depends(require_admin),
    db: Session = Depends(get_db),
) -> dict:
    """Read-only detail for one PME account.

    Always emits an ``audit_log admin_view`` row before returning (US2).
    """
    try:
        payload = pme_view.get_account_detail(
            db,
            account_id=account_id,
            section=section,
            request=request,
            admin_user_id=admin.id,
        )
    except RuntimeError as exc:
        # Fail-closed: never serve an admin consultation without a trace.
        raise HTTPException(
            status_code=503, detail={"code": "audit_unavailable", "message": str(exc)}
        ) from exc
    if not payload:
        raise HTTPException(
            status_code=404, detail={"code": "not_found", "message": "PME introuvable"}
        )
    return payload
