"""F57 / US2 — Handler READ ``recall_history`` (P9 strict, FR-006).

Le LLM peut invoquer ``recall_history(query, limit)`` via le dispatcher F55
(catégorie READ → REINVOKE_LLM). Le handler :

1. Récupère ``thread_id``/``account_id`` depuis le state.
2. Calcule (ou réutilise du cache) l'embedding Voyage de ``args.query``
   (US8 NFR-008).
3. Cosine search top-K bornée au thread courant via ``long_term.search_long_term``
   (scope strict ``thread_id`` + ``account_id``).
4. Tronque ``content_preview`` selon ``LLM_AGENT_RECALL_HISTORY_MAX_TOKENS``.
5. Stage une ligne ``recall_log`` (recall_type='tool') dans
   ``state.recall_log_entries`` (flush en fin de tour par le runner).

Le handler ne fait PAS de mutation (READ-only). Toute exception est
journalisée (best-effort) et retourne un résultat ``matches=[]`` plutôt que
de casser le tour LLM (NFR-008).
"""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.agent.memory import embedding_cache, long_term, recall_log
from app.agent.state import AgentState, ValidatedToolCall
from app.config import get_settings
from app.embeddings_client import hash_query

logger = logging.getLogger(__name__)

#: Cap dur sur ``limit`` (cohérent contrats/recall-history-tool.md §schéma).
LIMIT_MAX: int = 10
#: Char budget approximatif pour 800 tokens (~3.5 chars/token FR).
PREVIEW_CHAR_BUDGET: int = 800 * 3
#: Char budget par match (preview).
PREVIEW_PER_MATCH_CHARS: int = 280


class RecallHistoryArgs(BaseModel):
    """Schéma strict (P9 ``extra='forbid'``) du tool ``recall_history``.

    Voir ``contracts/recall-history-tool.md`` §3 pour le contrat LLM.
    """

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        ...,
        min_length=1,
        max_length=256,
        description=(
            "Texte à chercher dans l'historique du thread courant (FR)."
        ),
    )
    limit: int = Field(
        default=5,
        ge=1,
        le=LIMIT_MAX,
        description="Nombre max de messages à retourner (1-10, default 5).",
    )


class RecallHistoryMatch(BaseModel):
    """Élément retourné par le tool — schéma strict."""

    model_config = ConfigDict(extra="forbid")

    message_id: UUID
    role: Literal["user", "assistant"]
    content_preview: str = Field(min_length=0)
    score: float = Field(ge=0.0, le=1.0)
    created_at: datetime


class RecallHistoryResult(BaseModel):
    """Retour standardisé du handler — sérialisé en ToolMessage par le dispatcher."""

    model_config = ConfigDict(extra="forbid")

    matches: list[RecallHistoryMatch] = Field(default_factory=list)
    truncated: bool = False


def _truncate(text_value: str, *, max_chars: int) -> tuple[str, bool]:
    """Tronque un texte sur ``max_chars`` (best-effort, ajoute "…")."""
    if not text_value:
        return "", False
    if len(text_value) <= max_chars:
        return text_value.strip(), False
    return text_value[: max_chars - 1].rstrip() + "…", True


def _get_session(state: AgentState) -> Session | None:
    """Ouvre une session DB lecture courte avec contexte RLS."""
    try:
        from app.db import SessionLocal
    except Exception:  # pragma: no cover
        return None
    db = SessionLocal()
    try:
        from sqlalchemy import text as _t

        db.execute(
            _t(f"SET LOCAL \"app.current_account_id\" = '{state.account_id}'")
        )
        if state.user_id:
            db.execute(
                _t(f"SET LOCAL \"app.current_user_id\" = '{state.user_id}'")
            )
    except Exception:  # pragma: no cover
        pass
    return db


async def handle_recall_history(
    args: RecallHistoryArgs,
    *,
    state: AgentState,
) -> RecallHistoryResult:
    """Exécute le tool ``recall_history`` (US2).

    Args:
        args: Pydantic strict ``RecallHistoryArgs``.
        state: AgentState courant (pour cache embedding + RLS context).

    Returns:
        ``RecallHistoryResult`` (matches + truncated flag).
    """
    settings = get_settings()
    max_tokens = int(settings.LLM_AGENT_RECALL_HISTORY_MAX_TOKENS)
    char_budget = max_tokens * 3
    cleaned = (args.query or "").strip()
    if not cleaned:
        return RecallHistoryResult(matches=[], truncated=False)

    db = _get_session(state)
    if db is None:
        return RecallHistoryResult(matches=[], truncated=False)

    try:
        t0 = time.perf_counter()

        # Embedding (cache au scope tour) ----------------------------------
        vec = await embedding_cache.get_or_compute(
            state, thread_id=state.thread_id, query=cleaned
        )
        if vec is None:
            # Voyage indisponible → log warning + matches=[] (NFR-008)
            logger.warning("recall_history: embedding unavailable (degraded)")
            return RecallHistoryResult(matches=[], truncated=False)

        # Cosine search bornée au thread courant ---------------------------
        results = long_term.search_long_term(
            db,
            thread_id=state.thread_id,
            account_id=state.account_id,
            query_embedding=vec,
            exclude_message_ids=None,
            limit=int(args.limit),
            threshold=long_term.TOOL_DEFAULT_THRESHOLD,
            only_non_compacted=False,
        )
        latency_ms = int((time.perf_counter() - t0) * 1000)

        # Tronquage ---------------------------------------------------------
        truncated = False
        chars_used = 0
        matches: list[RecallHistoryMatch] = []
        for m in results:
            preview, was_trunc = _truncate(
                m.content, max_chars=PREVIEW_PER_MATCH_CHARS
            )
            if was_trunc:
                truncated = True
            chars_used += len(preview)
            if chars_used > char_budget and matches:
                truncated = True
                break
            try:
                matches.append(
                    RecallHistoryMatch(
                        message_id=m.message_id,
                        role=m.role if m.role in ("user", "assistant") else "user",
                        content_preview=preview,
                        score=max(0.0, min(1.0, float(m.score))),
                        created_at=m.created_at,
                    )
                )
            except Exception as exc:  # noqa: BLE001
                logger.debug("recall_history skip invalid match: %s", exc)
                continue

        # Stage recall_log entry ('tool') ---------------------------------
        top_scores: list[dict[str, Any]] = [
            {
                "message_id": str(m.message_id),
                "score": round(float(m.score), 4),
            }
            for m in matches
        ]
        try:
            entry = recall_log.stage_entry(
                recall_type="tool",
                thread_id=str(state.thread_id),
                account_id=state.account_id,
                query_hash=hash_query(cleaned),
                top_k=int(args.limit),
                top_scores=top_scores,
                latency_ms=latency_ms,
                agent_run_id=state.agent_run_id,
            )
            # Le runner flush en fin de tour. Mais comme on est dans un
            # handler READ qui n'a pas accès direct au reducer, on append
            # via la liste mutable du state (ATTENTION : non thread-safe,
            # mais le tour est mono-coroutine).
            state.recall_log_entries.append(entry)
        except Exception as exc:  # noqa: BLE001
            logger.warning("recall_history: stage_entry failed: %s", exc)

        return RecallHistoryResult(matches=matches, truncated=truncated)
    except Exception as exc:  # noqa: BLE001
        logger.warning("recall_history: handler failed (degraded): %s", exc)
        return RecallHistoryResult(matches=[], truncated=False)
    finally:
        try:
            db.close()
        except Exception:  # pragma: no cover
            pass


# --- Adapter dispatcher F55 ---------------------------------------------


async def recall_history_handler_dispatch(
    state: AgentState, call: ValidatedToolCall
) -> dict[str, Any]:
    """Adapter ``_REINVOKE_HANDLERS`` (signature ``(state, call) -> dict``).

    Le dispatcher F55 sérialise ensuite le résultat en ToolMessage JSON.
    """
    args = call.arguments
    if not isinstance(args, RecallHistoryArgs):
        # Coerce defensively
        try:
            args = RecallHistoryArgs.model_validate(
                args.model_dump() if hasattr(args, "model_dump") else dict(args)
            )
        except Exception as exc:  # noqa: BLE001
            return {
                "matches": [],
                "truncated": False,
                "error": f"invalid_args: {exc!s}"[:200],
            }
    result = await handle_recall_history(args, state=state)
    return result.model_dump(mode="json")


def register() -> None:
    """Enregistre le handler dans ``_REINVOKE_HANDLERS`` (idempotent)."""
    try:
        from app.agent.nodes.dispatch_tool import _REINVOKE_HANDLERS
    except Exception as exc:  # pragma: no cover
        logger.warning("recall_history register failed: %s", exc)
        return
    _REINVOKE_HANDLERS.setdefault(
        "recall_history", recall_history_handler_dispatch
    )


__all__ = [
    "LIMIT_MAX",
    "PREVIEW_PER_MATCH_CHARS",
    "RecallHistoryArgs",
    "RecallHistoryMatch",
    "RecallHistoryResult",
    "handle_recall_history",
    "recall_history_handler_dispatch",
    "register",
]
