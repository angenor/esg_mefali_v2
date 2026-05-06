"""F54 — Nœud ``build_context`` : construit le system prompt dynamique.

Réécriture F54 du squelette F53 (qui ne posait qu'un SystemMessage statique).
Ce nœud :

1. Charge :class:`BusinessContext` (loader + cache LRU+TTL hybride).
2. Charge :class:`EnrichedPageContext` (lecture page courante).
3. Construit le prompt via :func:`build_system_prompt` (identité +
   invariants + business + page + tools + skills + sheet_result + ...).
4. Stocke ``state.system_prompt`` (string final) et le ``system_prompt_hash``
   sera persisté en fin de run par le runner.

Le nœud ajoute aussi le ``HumanMessage`` du tour courant à
``state.messages`` (compat F53).

Le node est tolérant : si la DB est indisponible ou si une lecture échoue,
on construit un prompt minimal avec uniquement identité + invariants pour
ne pas casser le tour utilisateur.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from langchain_core.messages import HumanMessage, SystemMessage

from app.agent.context.cache import get_business_context_cache
from app.agent.context.hashing import compute_prompt_hash
from app.agent.context.models import (
    SCHEMA_VERSION,
    BusinessContext,
    EnrichedPageContext,
)
from app.agent.prompt_builder import build_system_prompt
from app.agent.prompts.invariants import PROMPT_VERSION
from app.agent.state import AgentState, Intent
from app.config import get_settings
from app.core.session import set_db_session_context
from app.db import SessionLocal

logger = logging.getLogger(__name__)

NODE_NAME = "build_context"

_FULL_CONTEXT_INTENTS = frozenset({Intent.PROFILAGE, Intent.MUTATION, Intent.ANALYSE})


_FALLBACK_SYSTEM_PROMPT = (
    "Tu es ESG Mefali, l'assistant IA pour PME ouest-africaines en finance "
    "verte. Tu réponds en français, tu cites tes sources via cite_source pour "
    "tout chiffre ESG ou financier."
)


async def node_build_context(state: AgentState) -> dict:
    """Construit le system prompt dynamique F54 (FR-004).

    Fait 1 appel DB synchrone enveloppé dans ``asyncio.to_thread`` (cf.
    :func:`load_business_context`) pour ne pas bloquer la boucle.
    """
    settings = get_settings()
    cache = get_business_context_cache()
    cache_hit = cache.get(state.account_id, SCHEMA_VERSION) is not None

    business_ctx, page_ctx = await _safe_load_contexts(state)

    try:
        prompt_str, _report = build_system_prompt(
            business_ctx=business_ctx,
            page_ctx=page_ctx,
            user_role=business_ctx.user_role,
            recent_messages=state.messages,
            metadata={"page": state.context_json.page_route},
            budget_tokens=settings.LLM_AGENT_PROMPT_BUDGET_TOKENS,
            encoding=settings.LLM_TIKTOKEN_ENCODING,
            cache_hit_business_ctx=cache_hit,
        )
    except Exception:  # noqa: BLE001
        logger.exception("build_system_prompt failed — fallback")
        prompt_str = _FALLBACK_SYSTEM_PROMPT

    new_messages: list = []
    has_system = any(isinstance(m, SystemMessage) for m in state.messages)
    if not has_system:
        new_messages.append(SystemMessage(content=prompt_str))
    new_messages.append(HumanMessage(content=state.user_message))

    return {
        "messages": new_messages,
        "system_prompt": prompt_str,
    }


async def _safe_load_contexts(
    state: AgentState,
) -> tuple[BusinessContext, EnrichedPageContext]:
    """Charge business_ctx + page_ctx avec fallback minimal en cas d'erreur DB."""
    try:
        from app.agent.context.loader import (
            load_business_context,
            load_page_context,
        )

        # Ouvre une session RLS-safe pour la durée du load.
        session = SessionLocal()
        try:
            set_db_session_context(
                session,
                user_id=state.user_id,
                account_id=state.account_id,
                is_admin=False,
            )
            business_ctx = await load_business_context(
                account_id=state.account_id,
                user_id=state.user_id,
                db=session,
                user_role="pme",
            )
            page_ctx = await load_page_context(
                {
                    "page_route": state.context_json.page_route,
                    "entity_type": _detect_entity_type(state.context_json.page_route),
                    "entity_id": str(state.context_json.entity_id)
                    if state.context_json.entity_id
                    else None,
                },
                account_id=state.account_id,
                db=session,
            )
            return business_ctx, page_ctx
        finally:
            try:
                session.close()
            except Exception:  # noqa: BLE001
                pass
    except Exception:  # noqa: BLE001
        logger.warning("F54 loader failed — minimal fallback context", exc_info=True)
        return _empty_business_context(state), _empty_page_context(state)


def _detect_entity_type(page_route: str | None) -> str | None:
    """Heuristique simple : ``/projet/<id>`` → Projet, etc."""
    if not page_route:
        return None
    p = page_route.strip("/").lower()
    parts = p.split("/")
    if not parts:
        return None
    head = parts[0]
    mapping = {
        "projet": "Projet",
        "projets": "Projet",
        "candidature": "Candidature",
        "candidatures": "Candidature",
        "indicateur": "Indicateur",
        "indicateurs": "Indicateur",
        "scoring": "Scoring",
    }
    return mapping.get(head)


def _empty_business_context(state: AgentState) -> BusinessContext:
    return BusinessContext(
        account_id=state.account_id,
        user_id=state.user_id,
        user_role="pme",
        loaded_at=datetime.now(UTC),
    )


def _empty_page_context(state: AgentState) -> EnrichedPageContext:
    return EnrichedPageContext(
        page=state.context_json.page_route,
        entity_type=None,
        entity_id=None,
    )


def is_full_context(intent: Intent | None) -> bool:
    """Indique si l'intent demande un contexte complet (compat F53)."""
    return intent in _FULL_CONTEXT_INTENTS


def compute_state_prompt_hash(state: AgentState) -> str | None:
    """Helper FR-015 : retourne le hash SHA-256 du system prompt courant."""
    if not state.system_prompt:
        return None
    return compute_prompt_hash(state.system_prompt)


def get_prompt_version() -> str:
    """Helper FR-015 : version du template d'invariants courant."""
    return PROMPT_VERSION


__all__ = [
    "NODE_NAME",
    "compute_state_prompt_hash",
    "get_prompt_version",
    "is_full_context",
    "node_build_context",
]
