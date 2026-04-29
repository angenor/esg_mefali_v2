"""F04 — Candidature submit + recompute-from-snapshot (US6)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Annotated, Any
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.audit.helper import record_audit
from app.audit.schemas import SourceOfChange
from app.auth.dependencies import get_current_user
from app.db import get_db
from app.models.account_user import AccountUser
from app.snapshot.builder import SnapshotBuilderError, build_candidature_snapshot
from app.snapshot.recompute import detect_drift, recompute_from_snapshot

router = APIRouter(prefix="/candidatures", tags=["candidatures"])


@router.post("/{cid}/submit")
def submit_candidature(
    cid: UUID,
    user: Annotated[AccountUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Submit a candidature: build snapshot + set submitted_at atomically."""
    try:
        snapshot = build_candidature_snapshot(db, candidature_id=cid)
    except SnapshotBuilderError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"error": "snapshot_build_failed", "message": str(exc)},
        ) from exc

    import json as _json

    db.execute(
        text(
            "UPDATE candidature "
            "SET snapshot_json = CAST(:snap AS JSONB), "
            "    submitted_at  = :ts, "
            "    soumission_at = :ts, "
            "    statut = 'submitted' "
            "WHERE id = :cid AND submitted_at IS NULL"
        ),
        {"snap": _json.dumps(snapshot), "ts": datetime.now(tz=UTC), "cid": str(cid)},
    )
    record_audit(
        db,
        entity_type="candidature",
        entity_id=cid,
        field="submitted_at",
        old=None,
        new=datetime.now(tz=UTC).isoformat(),
        source_of_change=SourceOfChange.MANUAL,
        user_id=str(user.id),
        account_id=str(user.account_id) if user.account_id else None,
    )
    db.commit()
    return {"id": str(cid), "snapshot": snapshot}


@router.post("/{cid}/recompute-from-snapshot")
def recompute_endpoint(
    cid: UUID,
    user: Annotated[AccountUser, Depends(get_current_user)],
    db: Annotated[Session, Depends(get_db)],
) -> dict[str, Any]:
    """Recompute the score from a candidature's frozen snapshot.

    Always returns HTTP 200, even on drift (FR-022). Drift is signaled by
    ``drift_detected=true`` in the body and a ``score_drift`` audit row.
    """
    cand = db.execute(
        text("SELECT snapshot_json FROM candidature WHERE id = CAST(:cid AS UUID)"),
        {"cid": str(cid)},
    ).mappings().first()
    if cand is None or cand["snapshot_json"] is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"error": "snapshot_not_found"},
        )

    snapshot = cand["snapshot_json"]
    recomputed = recompute_from_snapshot(snapshot)
    drift = detect_drift(snapshot, recomputed)
    snapshotted_amount = snapshot["scores"]["global"]["amount"]
    snapshotted_currency = snapshot["scores"]["global"]["currency"]

    if drift:
        record_audit(
            db,
            entity_type="candidature",
            entity_id=cid,
            field="score_drift",
            old={"amount": snapshotted_amount, "currency": snapshotted_currency},
            new={"amount": recomputed.amount, "currency": recomputed.currency},
            source_of_change=SourceOfChange.SYSTEM,
            user_id=str(user.id),
            account_id=str(user.account_id) if user.account_id else None,
        )
        db.commit()

    snapshotted_decimal = Decimal(snapshotted_amount)
    return {
        "candidature_id": str(cid),
        "snapshotted": {"amount": snapshotted_amount, "currency": snapshotted_currency},
        "recomputed": {"amount": recomputed.amount, "currency": recomputed.currency},
        "drift_detected": drift,
        "delta": str(recomputed.to_decimal() - snapshotted_decimal),
    }
