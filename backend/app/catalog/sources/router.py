"""F07 — Router admin pour le catalogue Sources (US1 MVP).

Routes :
- ``POST /admin/sources`` (create, statut pending) — admin only.
- ``GET  /admin/sources/{id}`` (read) — admin only.

Différé (P2/P3) : list + filtres avancés US3, verify/mark-outdated US2,
impact US4, page publique US5, unsourced claims US6.
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_admin
from app.catalog.sources.schemas import SourceCreate, SourceCreated, SourceRead
from app.catalog.sources.service import create_source
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter(prefix="/admin/sources", tags=["admin-sources"])


@router.post(
    "",
    response_model=SourceCreated,
    status_code=status.HTTP_201_CREATED,
)
def post_create_source(
    payload: SourceCreate,
    admin: AccountUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> SourceCreated:
    """Crée une nouvelle source en statut ``pending``."""
    row, head_warning = create_source(
        db, payload, actor_id=admin.id, run_probe=False
    )
    db.commit()
    return SourceCreated(
        source=SourceRead.model_validate(row), head_warning=head_warning
    )


@router.get("/{source_id}", response_model=SourceRead)
def get_source(
    source_id: uuid.UUID,
    _admin: AccountUser = Depends(get_current_admin),
    db: Session = Depends(get_db),
) -> SourceRead:
    """Lecture admin unitaire d'une source (peu importe le statut)."""
    row = db.execute(
        text(
            "SELECT id, url, canonical_url, title, publisher, version, "
            "date_publi, page, section, captured_at, captured_by, "
            "verified_by, verified_at, verification_status, notes "
            "FROM source WHERE id = :id"
        ),
        {"id": str(source_id)},
    ).mappings().first()
    if row is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Source introuvable."},
        )
    return SourceRead.model_validate(dict(row))


__all__ = ["router"]
