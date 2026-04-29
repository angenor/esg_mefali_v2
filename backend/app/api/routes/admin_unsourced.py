"""F03 US6 — Route admin agrégée des claims non sourcés."""

from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_user
from app.db import get_db
from app.schemas.source import UnsourcedClaimAggRow

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/unsourced-claims", response_model=list[UnsourcedClaimAggRow])
def list_unsourced_claims(
    _user=Depends(get_current_user),
    db: Session = Depends(get_db),
    days: int = Query(default=30, ge=1, le=365),
    limit: int = Query(default=50, ge=1, le=200),
) -> list[UnsourcedClaimAggRow]:
    """Renvoie les claims agrégés (RLS s'applique via app.current_account_id)."""
    rows = db.execute(
        text(
            """
            SELECT claim_text_normalized AS claim,
                   COUNT(*) AS freq,
                   MAX(created_at) AS last_seen
            FROM unsourced_claim_log
            WHERE created_at >= now() - (:days || ' days')::interval
            GROUP BY claim_text_normalized
            ORDER BY freq DESC, last_seen DESC
            LIMIT :limit
            """
        ),
        {"days": days, "limit": limit},
    ).mappings().all()
    return [UnsourcedClaimAggRow.model_validate(dict(r)) for r in rows]
