"""F32 + F52 US3 — Routes API ``/me/dashboard/*``, ``/me/data/*``, ``/me/exports``.

Endpoints :
- ``GET /me/dashboard/summary`` : agrégat lecture seule pour la page d'accueil.
- ``GET /me/data/export`` : export JSON complet du compte (US6 "Mes données").
- ``GET /me/exports`` : historique paginé (F52 US3).
- ``POST /me/exports`` : génère un nouvel export (202 + cycle pending → ready).
- ``GET /me/exports/{id}`` : détail (404/410).

Audit : chaque appel logue une ligne ``audit_log`` (best-effort).
"""

from __future__ import annotations

import logging
import uuid
from typing import Annotated

from fastapi import APIRouter, Body, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.dashboard.exports_service import (
    create_export,
    get_export,
    list_exports,
)
from app.dashboard.schemas import DashboardSummaryOut, DataExportOut
from app.dashboard.schemas_f52 import ExportCreate, ExportListOut, ExportOut
from app.dashboard.service import build_export, build_summary
from app.db import get_db
from app.models.account_user import AccountUser

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])


def _safe_audit(
    db: Session,
    *,
    account_id: uuid.UUID,
    user_id: uuid.UUID,
    action: str,
) -> None:
    """Best-effort audit. Ne fait jamais échouer la requête HTTP."""
    try:
        from app.audit.helper import record_audit

        record_audit(
            db,
            entity_type="account",
            entity_id=account_id,
            field=action,
            new={"action": action},
            source_of_change="manual",
            user_id=user_id,
            account_id=account_id,
        )
        db.commit()
    except Exception as exc:  # noqa: BLE001 — best-effort
        logger.warning("dashboard: audit log failed for action=%s: %s", action, exc)
        try:
            db.rollback()
        except Exception:  # pragma: no cover
            pass


@router.get("/me/dashboard/summary", response_model=DashboardSummaryOut)
def get_dashboard_summary(
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> DashboardSummaryOut:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "PME sans account_id."},
        )
    summary = build_summary(db, user.account_id)
    _safe_audit(
        db, account_id=user.account_id, user_id=user.id, action="dashboard_view"
    )
    return summary


@router.get("/me/data/export", response_model=DataExportOut)
def export_my_data(
    db: Session = Depends(get_db),
    user: AccountUser = Depends(get_current_pme),
) -> DataExportOut:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "PME sans account_id."},
        )
    export = build_export(db, user.account_id)
    _safe_audit(
        db, account_id=user.account_id, user_id=user.id, action="data_export"
    )
    return export


# ---------------------------------------------------------------------------
# F52 US3 — Historique & génération exports
# ---------------------------------------------------------------------------


@router.get("/me/exports", response_model=ExportListOut)
def list_me_exports(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    type: Annotated[list[str] | None, Query()] = None,
    cursor: Annotated[str | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 20,
) -> ExportListOut:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "PME sans account_id."},
        )
    return list_exports(
        db,
        account_id=user.account_id,
        types=type,
        cursor=cursor,
        limit=limit,
    )


@router.post(
    "/me/exports", response_model=ExportOut, status_code=status.HTTP_202_ACCEPTED
)
def create_me_export(
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
    body: Annotated[ExportCreate, Body()],
) -> ExportOut:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "PME sans account_id."},
        )
    out = create_export(db, user=user, payload=body)
    db.commit()
    return out


@router.get("/me/exports/{export_id}", response_model=ExportOut)
def get_me_export(
    export_id: uuid.UUID,
    user: Annotated[AccountUser, Depends(get_current_pme)],
    db: Annotated[Session, Depends(get_db)],
) -> ExportOut:
    if user.account_id is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"code": "no_account", "message": "PME sans account_id."},
        )
    out = get_export(db, account_id=user.account_id, export_id=export_id)
    if out is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "export_not_found"},
        )
    if out.status == "expired":
        raise HTTPException(
            status_code=status.HTTP_410_GONE,
            detail={"code": "export_expired"},
        )
    return out
