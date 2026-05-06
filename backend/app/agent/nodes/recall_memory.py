"""F54 / T071 — Nœud ``recall_memory`` : injecte les 15 derniers messages
historiques au format LangChain (FR-016).

Le nœud lit les messages persistés dans la table ``chat_message`` (F13)
filtrés par ``thread_id`` (composite ``{account}:{conv}``), tri ASC, cap
à 15 messages les plus récents (les anciens sont gérés par F57 via
``recall_history`` tool).

Tolère les schémas chat absents : si la lecture échoue, le nœud est
no-op (compat F53).
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agent.state import AgentState
from app.core.session import set_db_session_context
from app.db import SessionLocal

logger = logging.getLogger(__name__)

NODE_NAME = "recall_memory"


#: Limite F54 (FR-016) — au-delà, F57 prend le relais via ``recall_history``.
RECENT_HISTORY_CAP: int = 15


async def node_recall_memory(state: AgentState) -> dict:
    """Injecte les 15 derniers messages du thread dans ``state.messages``.

    Si ``state.messages`` contient déjà des messages historiques (au-delà
    du SystemMessage + HumanMessage courants), on suppose que le runner
    les a déjà chargés et on est no-op (idempotent).
    """
    # On ne touche pas si messages contient déjà des éléments ``user`` ou
    # ``assistant`` autres que le HumanMessage courant.
    user_msgs_count = sum(1 for m in state.messages if isinstance(m, HumanMessage))
    if user_msgs_count >= 2:
        return {}

    try:
        history = _load_recent_history_sync(state)
    except Exception:  # noqa: BLE001
        logger.debug("recall_memory: history load skipped", exc_info=True)
        return {}

    if not history:
        return {}

    # On insère l'historique **avant** le HumanMessage courant.
    # Le reducer ``add_messages`` LangGraph fera l'append.
    return {"messages": history}


def _load_recent_history_sync(state: AgentState) -> list[BaseMessage]:
    """Lit les ``RECENT_HISTORY_CAP`` derniers messages du thread.

    Retourne une liste vide si la table chat n'existe pas ou si aucune row.
    """
    # ``thread_id`` = ``account_uuid:conv_uuid`` — on extrait le suffixe.
    _, _, conv_uuid_str = state.thread_id.partition(":")
    if not conv_uuid_str:
        return []

    session: Session = SessionLocal()
    try:
        set_db_session_context(
            session,
            user_id=state.user_id,
            account_id=state.account_id,
            is_admin=False,
        )
        rows = session.execute(
            text(
                """
                SELECT role, content, created_at
                FROM chat_message
                WHERE thread_id = CAST(:tid AS UUID)
                  AND account_id = CAST(:aid AS UUID)
                ORDER BY created_at DESC
                LIMIT :lim
                """
            ),
            {
                "tid": conv_uuid_str,
                "aid": str(state.account_id),
                "lim": RECENT_HISTORY_CAP,
            },
        ).all()
    except Exception:  # noqa: BLE001
        return []
    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass

    if not rows:
        return []

    # Reverse (DESC → ASC) pour avoir l'ordre chronologique.
    rows = list(reversed(rows))

    out: list[BaseMessage] = []
    for r in rows:
        msg = _row_to_langchain_message(r)
        if msg is not None:
            out.append(msg)
    return out


def _row_to_langchain_message(row: Any) -> BaseMessage | None:
    role = (getattr(row, "role", None) or "").lower()
    content = getattr(row, "content", None) or ""
    if not content:
        return None
    if role in ("user", "human", "pme"):
        return HumanMessage(content=content)
    if role in ("assistant", "ai", "esg_mefali"):
        return AIMessage(content=content)
    if role in ("tool", "function"):
        return ToolMessage(content=content, tool_call_id="historical")
    if role == "system":
        return SystemMessage(content=content)
    return None


__all__ = ["NODE_NAME", "RECENT_HISTORY_CAP", "node_recall_memory"]
