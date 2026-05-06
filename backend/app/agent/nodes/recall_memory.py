"""F57 — Nœud LangGraph ``recall_memory`` (US1, RÉÉCRITURE TOTALE).

Ce nœud remplace le squelette F54 qui chargeait simplement les 15 derniers
messages SQL. Il implémente :

1. Chargement des ``LLM_AGENT_MEMORY_RECENT_COUNT`` (=15) derniers messages
   chronologiques (court terme, ``compacted=False``).
2. Si total messages > 15 : embed la ``user_message`` (cache) + cosine
   search top-K=3 messages anciens ≥ seuil 0.7 → insertion en tête avec
   préfixe ``[Souvenirs pertinents d'échanges précédents]``.
3. Si ``chat_thread.summary IS NOT NULL`` : insertion en TOUT premier avec
   préfixe ``[Résumé compacté des messages anciens]``.
4. Stage une ligne ``recall_log`` (recall_type='auto') dans
   ``state.recall_log_entries`` pour flush en fin de tour.
5. Mode dégradé sans crash si Voyage / pgvector indisponible (FR-014).

Référence : ``specs/057-agent-memory-rag/contracts/recall-memory-node.md``.
"""

from __future__ import annotations

import logging
import time
from typing import Any
from uuid import UUID

from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agent.memory import embedding_cache, long_term, recall_log
from app.agent.state import AgentState
from app.config import get_settings
from app.core.session import set_db_session_context
from app.db import SessionLocal
from app.embeddings_client import hash_query

logger = logging.getLogger(__name__)

NODE_NAME = "recall_memory"

# Conserve l'ancienne constante F54 pour compat tests ; F57 utilise
# settings.LLM_AGENT_MEMORY_RECENT_COUNT en runtime.
RECENT_HISTORY_CAP: int = 15

#: Préfixes des blocs SystemMessage injectés en tête (US1).
PREFIX_SUMMARY = "[Résumé compacté des messages anciens]"
PREFIX_LONG_TERM = "[Souvenirs pertinents d'échanges précédents]"


def _row_to_langchain_message(row: dict[str, Any]) -> BaseMessage | None:
    role = str(row.get("role") or "").lower()
    content = str(row.get("content") or "")
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


def _format_long_term_block(matches: list[long_term.LongTermMatch]) -> SystemMessage:
    """Formate le bloc ``[Souvenirs pertinents…]`` comme SystemMessage."""
    lines = [PREFIX_LONG_TERM]
    for m in matches:
        date_str = m.created_at.strftime("%Y-%m-%d") if m.created_at else "?"
        lines.append(f"({m.role}, {date_str}): {m.content}")
    return SystemMessage(content="\n---\n".join(lines))


def _format_summary_block(summary: str) -> SystemMessage:
    """Formate le bloc ``[Résumé compacté…]`` comme SystemMessage."""
    return SystemMessage(content=f"{PREFIX_SUMMARY}\n{summary}")


def _set_rls_context(session: Session, *, account_id, user_id) -> None:
    """Positionne les GUC RLS pour la session SQL."""
    try:
        session.execute(text(f"SET LOCAL app.current_account_id = '{account_id}'"))
        if user_id is not None:
            session.execute(text(f"SET LOCAL app.current_user_id = '{user_id}'"))
    except Exception:  # noqa: BLE001
        pass


def _get_thread_summary(
    session: Session, *, thread_id: str | UUID, account_id
) -> str | None:
    """Lit ``chat_thread.summary`` (None si absent ou si table indispo)."""
    conv_uuid = long_term._conv_uuid_from_thread_id(thread_id)  # noqa: SLF001
    if not conv_uuid:
        return None
    try:
        row = session.execute(
            text(
                """
                SELECT summary FROM chat_thread
                WHERE id = CAST(:tid AS UUID)
                  AND account_id = CAST(:aid AS UUID)
                """
            ),
            {"tid": conv_uuid, "aid": str(account_id)},
        ).first()
    except Exception:  # noqa: BLE001
        return None
    if not row:
        return None
    return row[0] if row[0] else None


async def node_recall_memory(state: AgentState) -> dict[str, Any]:
    """Charge le contexte mémoire pour le tour courant (US1).

    Voir docstring module pour le détail.
    """
    settings = get_settings()
    recent_count = int(settings.LLM_AGENT_MEMORY_RECENT_COUNT)
    top_k = int(settings.LLM_AGENT_MEMORY_TOP_K)
    threshold = float(settings.LLM_AGENT_MEMORY_THRESHOLD)

    # Idempotence : si state.messages contient déjà ≥ 2 HumanMessage, on
    # suppose que le chargement a déjà eu lieu. Sécurité au cas où.
    user_msgs_count = sum(1 for m in state.messages if isinstance(m, HumanMessage))
    if user_msgs_count >= 2:
        return {}

    session: Session = SessionLocal()
    try:
        set_db_session_context(
            session,
            user_id=state.user_id,
            account_id=state.account_id,
            is_admin=False,
        )
        # Sécurité supplémentaire (long_term scope explicit thread_id+account_id)
        _set_rls_context(session, account_id=state.account_id, user_id=state.user_id)

        # 1. Court terme — 15 derniers messages
        recent_rows = long_term.fetch_recent_messages(
            session,
            thread_id=state.thread_id,
            account_id=state.account_id,
            limit=recent_count,
        )
        recent_messages: list[BaseMessage] = []
        for r in recent_rows:
            msg = _row_to_langchain_message(r)
            if msg is not None:
                recent_messages.append(msg)

        # 2. Long terme — cosine search si total > 15
        total = long_term.count_thread_messages(
            session,
            thread_id=state.thread_id,
            account_id=state.account_id,
            only_non_compacted=True,
        )
        long_term_matches: list[long_term.LongTermMatch] = []
        recall_log_staged = False

        if total > recent_count and state.user_message:
            t0 = time.perf_counter()
            vec = await embedding_cache.get_or_compute(
                state, thread_id=state.thread_id, query=state.user_message
            )
            if vec is not None:
                exclude_ids = [str(r.get("id")) for r in recent_rows if r.get("id")]
                long_term_matches = long_term.search_long_term(
                    session,
                    thread_id=state.thread_id,
                    account_id=state.account_id,
                    query_embedding=vec,
                    exclude_message_ids=exclude_ids,
                    limit=top_k,
                    threshold=threshold,
                    only_non_compacted=True,
                )
                latency_ms = int((time.perf_counter() - t0) * 1000)

                # Stage recall_log entry (auto) — toujours staged même si 0 matches
                # car la recherche a été tentée (NFR-009).
                top_scores = [
                    {"message_id": str(m.message_id), "score": round(m.score, 4)}
                    for m in long_term_matches
                ]
                entry = recall_log.stage_entry(
                    recall_type="auto",
                    thread_id=str(state.thread_id),
                    account_id=state.account_id,
                    query_hash=hash_query(state.user_message),
                    top_k=top_k,
                    top_scores=top_scores,
                    latency_ms=latency_ms,
                    agent_run_id=state.agent_run_id,
                )
                # Append à state.recall_log_entries via patch (le reducer
                # _append concatène). On signal pour patch ci-dessous.
                recall_log_staged = True

        # 3. Summary block (si présent en DB)
        summary_text = _get_thread_summary(
            session, thread_id=state.thread_id, account_id=state.account_id
        )

    finally:
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass

    # 4. Compose la liste finale dans l'ordre requis :
    #    summary → souvenirs longs → court terme
    final_messages: list[BaseMessage] = []
    if summary_text:
        final_messages.append(_format_summary_block(summary_text))
    if long_term_matches:
        final_messages.append(_format_long_term_block(long_term_matches))
    final_messages.extend(recent_messages)

    if not final_messages and not recall_log_staged:
        # Aucun message à injecter et aucun recall tenté → no-op
        return {}

    patch: dict[str, Any] = {}
    if final_messages:
        patch["messages"] = final_messages
    if recall_log_staged:
        # On utilise le reducer _append : passer une liste à 1 entry
        patch["recall_log_entries"] = [entry]
    return patch


__all__ = [
    "NODE_NAME",
    "PREFIX_LONG_TERM",
    "PREFIX_SUMMARY",
    "RECENT_HISTORY_CAP",
    "node_recall_memory",
]
