"""F55 — ``MutationCtx`` immuable.

Regroupe toutes les dépendances d'un handler de mutation (FR-006).
Frozen dataclass → asyncio-safe (NFR-004), partage interdit entre tool calls.

Référence : ``specs/055-agent-tool-dispatch-sse/data-model.md`` §2.3.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any
from uuid import UUID

from sqlalchemy.orm import Session


@dataclass(frozen=True)
class MutationCtx:
    """Contexte d'exécution d'un handler de mutation.

    Champs :
    - ``account_id`` / ``user_id`` : identité tenant (P2 RLS).
    - ``db`` : session SQLAlchemy déjà sous contexte ``app.current_account_id``.
    - ``audit_logger`` : callable ``record_audit`` partiellement appliqué.
    - ``event_bus_publisher`` : ``async (account_id, event_type, payload) -> None``.
    - ``tool_call_log_id`` : id de la ligne ``tool_call_log`` créée pour ce dispatch.
    - ``agent_run_id`` : id du run agent (pour traçabilité).
    - ``dry_run`` : si True, le dispatcher ROLLBACK la transaction (US6).
    """

    account_id: UUID
    user_id: UUID
    db: Session
    audit_logger: Callable[..., UUID | None]
    event_bus_publisher: Callable[[UUID, str, dict[str, Any]], Awaitable[None]]
    tool_call_log_id: UUID
    agent_run_id: UUID | None = None
    dry_run: bool = False


__all__ = ["MutationCtx"]
