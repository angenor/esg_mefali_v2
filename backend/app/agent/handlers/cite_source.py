"""F56 — Handler READ ``cite_source`` (FR-003).

Vérifie en DB que ``Source`` existe et est ``verification_status='verified'``.
Strict (Q3 clarification) : ``pending``, ``outdated``, ``rejected`` sont
**toujours** rejetés. Sur succès, retourne le metadata sérialisé pour
ToolMessage ; sur échec, retourne une erreur structurée.

Le handler est enregistré dans ``app.agent.nodes.dispatch_tool._REINVOKE_HANDLERS``
au boot via ``register_sourcing_handlers``.
"""

from __future__ import annotations

import logging
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agent.state import AgentState, ValidatedToolCall

logger = logging.getLogger(__name__)


def _get_session(state: AgentState) -> Session | None:
    """Récupère une session DB pour la lecture (best-effort).

    Le runner F53 ouvre déjà une session par tour ; ici on ouvre une
    nouvelle session courte (READ uniquement) avec contexte RLS.
    """
    try:
        from app.db import SessionLocal
    except Exception:  # pragma: no cover
        return None
    db = SessionLocal()
    try:
        db.execute(
            text(
                f"SET LOCAL \"app.current_account_id\" = '{state.account_id}'"
            )
        )
        if state.user_id:
            db.execute(
                text(f"SET LOCAL \"app.current_user_id\" = '{state.user_id}'")
            )
    except Exception:  # pragma: no cover
        pass
    return db


async def cite_source_handler(
    state: AgentState, call: ValidatedToolCall
) -> dict[str, Any]:
    """Vérifie ``Source(source_id)`` et retourne metadata ou erreur structurée.

    Args:
        state: Agent state (account_id, user_id pour RLS).
        call: Tool call validé (``arguments.source_id`` UUID).

    Returns:
        dict :
        - succès → ``{source_id, title, publisher, url, page, section,
                      version, verification_status='verified'}``
        - erreur → ``{error: 'source_not_found' | 'source_unverified',
                       source_id, current_status?, hint}``
    """
    args = call.arguments
    source_id = getattr(args, "source_id", None)
    if source_id is None:
        return {
            "error": "source_not_found",
            "source_id": None,
            "hint": "use search_source to find a real source_id",
        }

    db = _get_session(state)
    if db is None:
        return {
            "error": "source_not_found",
            "source_id": str(source_id),
            "hint": "database unavailable",
        }
    try:
        row = db.execute(
            text(
                "SELECT id, title, publisher, url, canonical_url, page, "
                "section, version, verification_status "
                "FROM source WHERE id = :sid"
            ),
            {"sid": str(source_id)},
        ).mappings().first()
    except Exception as exc:  # noqa: BLE001
        logger.warning("cite_source DB query failed: %s", exc)
        return {
            "error": "source_not_found",
            "source_id": str(source_id),
            "hint": "use search_source to find a real source_id",
        }
    finally:
        try:
            db.close()
        except Exception:  # pragma: no cover
            pass

    if row is None:
        return {
            "error": "source_not_found",
            "source_id": str(source_id),
            "hint": "use search_source to find a real source_id",
        }

    status = row.get("verification_status")
    if status != "verified":
        return {
            "error": "source_unverified",
            "source_id": str(source_id),
            "current_status": status,
            "hint": "search_source for a verified alternative or flag_unsourced",
        }

    return {
        "source_id": str(row["id"]),
        "title": row["title"],
        "publisher": row["publisher"],
        "url": row.get("canonical_url") or row.get("url"),
        "page": row.get("page"),
        "section": row.get("section"),
        "version": row.get("version"),
        "verification_status": "verified",
    }


__all__ = ["cite_source_handler"]
