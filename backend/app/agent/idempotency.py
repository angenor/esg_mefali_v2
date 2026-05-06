"""F55 — Idempotence DB-backed (FR-011).

Clé ``idempotency_key = sha256(account_id:agent_run_id:call_id)[:32]``.
``find_existing`` interroge ``tool_call_log`` (UNIQUE per account_id, key).
``reconstruct_result`` rebuild un ``ToolDispatchResult`` depuis la row.

Permet la résilience SSE reconnect (FR-018 reconnect, NFR sécurité).
"""

from __future__ import annotations

import hashlib
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agent.state import DispatchCategory, ToolDispatchResult

logger = logging.getLogger(__name__)


def compute_idempotency_key(
    account_id: UUID,
    agent_run_id: UUID | None,
    call_id: str,
) -> str:
    """Calcule la clé d'idempotence sha256 32-char.

    Si ``agent_run_id`` est None, on utilise le sentinel ``no-run``.
    """
    raw = f"{account_id}:{agent_run_id or 'no-run'}:{call_id}"
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()[:32]


def find_existing(
    db: Session,
    *,
    account_id: UUID,
    idempotency_key: str,
) -> dict[str, Any] | None:
    """Cherche une ligne tool_call_log déjà committée pour cette clé.

    Utilise SELECT FOR SHARE pour éviter une race avec un dispatch concurrent.
    Retourne le row sous forme de dict, ou None si absent.
    """
    row = (
        db.execute(
            text(
                """
                SELECT id, tool_call_id, tool_name, status,
                       dispatch_result_kind, output_json, error_summary,
                       entity_type, entity_id, audit_log_id, is_dry_run
                FROM tool_call_log
                WHERE account_id = CAST(:aid AS UUID)
                  AND idempotency_key = :ikey
                LIMIT 1
                FOR SHARE
                """
            ),
            {"aid": str(account_id), "ikey": idempotency_key},
        )
        .mappings()
        .first()
    )
    if row is None:
        return None
    return dict(row)


def reconstruct_result(row: dict[str, Any]) -> ToolDispatchResult:
    """Rebuild un ``ToolDispatchResult`` depuis une row tool_call_log."""
    kind = row.get("dispatch_result_kind")
    # Heuristique de mapping vers DispatchCategory legacy
    if kind == "frontend_event":
        category = DispatchCategory.SSE_ONLY
    elif kind == "mutation_result":
        category = DispatchCategory.DB_MUTATION
    elif kind == "tool_message":
        category = DispatchCategory.REINVOKE_LLM
    else:
        category = DispatchCategory.DB_MUTATION  # default safe

    return ToolDispatchResult(
        tool_call_id=row.get("tool_call_id") or "",
        tool_name=row.get("tool_name") or "",
        category=category,
        status=row.get("status") or "ok",  # type: ignore[arg-type]
        kind=kind,
        output=row.get("output_json"),
        error_summary=row.get("error_summary"),
        entity_type=row.get("entity_type"),
        entity_id=row.get("entity_id"),
        audit_log_id=row.get("audit_log_id"),
        is_dry_run=bool(row.get("is_dry_run") or False),
    )


__all__ = [
    "compute_idempotency_key",
    "find_existing",
    "reconstruct_result",
]
