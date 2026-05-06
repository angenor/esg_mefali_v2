"""F55 — Confirmation flow pour mutations destructives (FR-012, US3).

``store_pending_confirmation`` persiste un ``PendingConfirmation`` dans
``agent_run.metadata['pending_confirmations'][call_id]`` avec ``expires_at``.
``consume_confirmation`` lit + supprime ; retourne la confirmation seulement
si non expirée ET si l'utilisateur a répondu "yes".

TTL configurable via ``LLM_AGENT_CONFIRMATION_TTL_SECONDS`` (défaut 180 s).
"""

from __future__ import annotations

import json
import logging
from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agent.state import PendingConfirmation

logger = logging.getLogger(__name__)


def get_confirmation_ttl_seconds() -> int:
    """Retourne le TTL configuré (défaut 180 s)."""
    try:
        from app.config import get_settings

        return int(getattr(get_settings(), "LLM_AGENT_CONFIRMATION_TTL_SECONDS", 180))
    except Exception:  # pragma: no cover - defensive
        return 180


def is_expired(pending: PendingConfirmation, *, now: datetime | None = None) -> bool:
    """True si la confirmation a dépassé son TTL."""
    current = now or datetime.now(UTC)
    expires = pending.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    return current >= expires


def build_pending_confirmation(
    *,
    tool_call_id: str,
    tool_name: str,
    arguments: dict[str, Any],
    ttl_seconds: int | None = None,
) -> PendingConfirmation:
    """Construit un ``PendingConfirmation`` avec ``expires_at = now + ttl``."""
    ttl = ttl_seconds if ttl_seconds is not None else get_confirmation_ttl_seconds()
    return PendingConfirmation(
        tool_call_id=tool_call_id,
        tool_name=tool_name,
        arguments=arguments,
        expires_at=datetime.now(UTC) + timedelta(seconds=ttl),
    )


def _read_metadata(db: Session, agent_run_id: UUID) -> dict[str, Any]:
    row = (
        db.execute(
            text(
                "SELECT metadata FROM agent_run "
                "WHERE id = CAST(:rid AS UUID) LIMIT 1"
            ),
            {"rid": str(agent_run_id)},
        )
        .mappings()
        .first()
    )
    if row is None:
        return {}
    metadata = row.get("metadata") or {}
    if isinstance(metadata, str):
        try:
            return json.loads(metadata)
        except Exception:  # pragma: no cover
            return {}
    return dict(metadata)


def _write_metadata(
    db: Session, agent_run_id: UUID, metadata: dict[str, Any]
) -> None:
    db.execute(
        text(
            "UPDATE agent_run SET metadata = CAST(:meta AS JSONB) "
            "WHERE id = CAST(:rid AS UUID)"
        ),
        {"meta": json.dumps(metadata, default=str), "rid": str(agent_run_id)},
    )


def store_pending_confirmation(
    db: Session,
    *,
    agent_run_id: UUID,
    pending: PendingConfirmation,
) -> None:
    """Stocke ``pending`` dans ``agent_run.metadata['pending_confirmations']``.

    Best-effort : si l'UPDATE échoue (rôle insuffisant), on log warning et
    on continue — le flow utilisateur ne doit pas être bloqué côté chat.
    """
    try:
        meta = _read_metadata(db, agent_run_id)
        pcs = meta.get("pending_confirmations") or {}
        if not isinstance(pcs, dict):
            pcs = {}
        pcs[pending.tool_call_id] = pending.model_dump(mode="json")
        meta["pending_confirmations"] = pcs
        _write_metadata(db, agent_run_id, meta)
    except Exception:  # noqa: BLE001
        logger.warning(
            "store_pending_confirmation failed for run=%s call=%s",
            agent_run_id,
            pending.tool_call_id,
            exc_info=True,
        )


def consume_confirmation(
    db: Session,
    *,
    agent_run_id: UUID,
    call_id: str,
    user_response: Literal["yes", "no"],
) -> tuple[PendingConfirmation | None, str]:
    """Lit, supprime et retourne (PendingConfirmation, status).

    Retourne :
    - (PendingConfirmation, "ok") si non expiré et user_response='yes'
    - (None, "cancelled_by_user") si user_response='no'
    - (None, "confirmation_expired") si expiré
    - (None, "missing") si aucun pending pour ``call_id``
    """
    try:
        meta = _read_metadata(db, agent_run_id)
        pcs = meta.get("pending_confirmations") or {}
        if not isinstance(pcs, dict) or call_id not in pcs:
            return None, "missing"

        raw = pcs.pop(call_id)
        meta["pending_confirmations"] = pcs
        _write_metadata(db, agent_run_id, meta)

        try:
            pending = PendingConfirmation.model_validate(raw)
        except Exception:  # pragma: no cover
            logger.warning("Invalid pending_confirmation in metadata, dropping")
            return None, "missing"

        if is_expired(pending):
            return None, "confirmation_expired"
        if user_response == "no":
            return None, "cancelled_by_user"
        return pending, "ok"
    except Exception:  # noqa: BLE001
        logger.warning("consume_confirmation failed", exc_info=True)
        return None, "missing"


__all__ = [
    "build_pending_confirmation",
    "consume_confirmation",
    "get_confirmation_ttl_seconds",
    "is_expired",
    "store_pending_confirmation",
]
