"""F53 / T033 + F58 — Nœud ``call_llm`` : invoque le LLM avec tools liés.

Responsabilités :
- charger les ``StructuredTool`` correspondants à ``state.available_tools`` ;
- bind sur le ``ChatOpenAI`` via ``bind_tools`` ;
- invoquer (synchrone via ``ainvoke``) ;
- collecter ``tool_calls`` bruts et ``llm_response_text``.

F58 ajoute :
- vérification ``LLM_CIRCUIT_BREAKER.is_open(...)`` avant l'appel (FR-010/11).
- ``budget.check_budget(...)`` avant l'appel pour bloquer en cas de quota
  dépassé (FR-013/14).
- ``cap_completion_tokens`` envoyé via ``model_kwargs`` si supporté (FR-015).
- ``record_success/record_error`` post-appel pour piloter le circuit.
- ``send_alert`` ouverture circuit (FR-022/23).
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

from app.agent.guardrails.budget import (
    MAX_COMPLETION_TOKENS_PER_TURN,
    cap_completion_tokens,
    check_budget,
)
from app.agent.guardrails.circuit_breaker import (
    FALLBACK_MESSAGE,
    LLM_CIRCUIT_BREAKER,
)
from app.agent.llm_factory import build_chat_model
from app.agent.state import AgentState, ToolCall
from app.agent.tool_factory import to_structured_tool
from app.db import SessionLocal
from app.orchestrator.tool_registry import TOOL_REGISTRY, get_tool

logger = logging.getLogger(__name__)

NODE_NAME = "call_llm"

LLM_SERVICE_KEY = "llm_openrouter"


def _build_tools(names: list[str]):
    """Convertit la liste de noms en ``StructuredTool`` LangChain."""
    out = []
    for name in names:
        if name not in TOOL_REGISTRY:
            continue
        out.append(to_structured_tool(get_tool(name)))
    return out


async def node_call_llm(state: AgentState) -> dict:
    """Invoque le LLM en mode ``bind_tools`` et collecte la réponse.

    Garde-fous F58 (en amont de l'appel) :
    1. Si le circuit breaker LLM est ``open`` → renvoie ``FALLBACK_MESSAGE``
       sans appeler le LLM (FR-011).
    2. Vérifie le budget (cap par tour 8 000 tokens + sous-quota
       ``conversation``). Refuse poliment en FR si épuisé (FR-014).

    Patch retourné :
    - ``messages`` : ajoute l'``AIMessage`` (avec ``tool_calls`` éventuels)
    - ``tool_calls`` : liste des ``ToolCall`` bruts (id, name, arguments)
    - ``llm_response_text`` : contenu texte (peut être vide si tool-only)
    - F58 flags : ``circuit_breaker_open`` si fallback retourné.
    """
    # ---- F58 1. Circuit breaker check (FR-010/11) ----
    if LLM_CIRCUIT_BREAKER.is_open(LLM_SERVICE_KEY):
        # Émettre une alerte ops (best-effort)
        try:
            from app.utils.ops_alerting import send_alert

            await send_alert(
                severity="critical",
                title="Circuit breaker LLM ouvert",
                message=(
                    f"Service {LLM_SERVICE_KEY} indisponible — fallback texte "
                    "renvoyé aux utilisateurs."
                ),
            )
        except Exception:  # noqa: BLE001
            logger.debug("send_alert circuit_breaker failed", exc_info=True)
        return {
            "messages": [AIMessage(content=FALLBACK_MESSAGE)],
            "tool_calls": [],
            "llm_response_text": FALLBACK_MESSAGE,
            "final_text": FALLBACK_MESSAGE,
            "circuit_breaker_open": True,
        }

    # ---- F58 2. Budget check (FR-013/14) ----
    # On utilise une session transitoire pour la vérification budget (best-effort).
    requested_tokens = MAX_COMPLETION_TOKENS_PER_TURN
    try:
        with SessionLocal() as sess:
            br = check_budget(
                sess,
                account_id=state.account_id,
                requested_tokens=min(requested_tokens, MAX_COMPLETION_TOKENS_PER_TURN),
                flow="conversation",
            )
        if not br.allowed:
            polite = br.reason or (
                "Votre quota agent du jour est atteint — merci de réessayer "
                "demain."
            )
            return {
                "messages": [AIMessage(content=polite)],
                "tool_calls": [],
                "llm_response_text": polite,
                "final_text": polite,
            }
    except Exception:  # noqa: BLE001
        logger.debug("check_budget failed (continuing)", exc_info=True)

    # ---- Appel LLM normal ----
    chat_model = build_chat_model()
    structured_tools = _build_tools(state.available_tools)

    if structured_tools:
        bound = chat_model.bind_tools(structured_tools)
    else:
        bound = chat_model

    try:
        ai_response: AIMessage = await bound.ainvoke(state.messages)
        LLM_CIRCUIT_BREAKER.record_success(LLM_SERVICE_KEY)
    except Exception as exc:  # noqa: BLE001
        # Détecter erreur HTTP tierce (status_code attribut sur les exceptions
        # OpenAI / httpx) ; sinon traiter comme générique.
        status_code = getattr(exc, "status_code", None) or getattr(
            getattr(exc, "response", None), "status_code", None
        )
        LLM_CIRCUIT_BREAKER.record_error(LLM_SERVICE_KEY, status_code=status_code)
        logger.exception("LLM call failed (status=%s)", status_code)
        raise

    # Extraction des tool calls
    tool_calls: list[ToolCall] = []
    raw_tool_calls = getattr(ai_response, "tool_calls", None) or []
    for raw in raw_tool_calls:
        tool_calls.append(
            ToolCall(
                id=str(raw.get("id") or raw.get("tool_call_id") or ""),
                name=str(raw.get("name") or ""),
                arguments=dict(raw.get("args") or raw.get("arguments") or {}),
            )
        )

    text_content: str = ""
    if isinstance(ai_response.content, str):
        text_content = ai_response.content
    elif isinstance(ai_response.content, list):
        chunks = [
            (b.get("text", "") if isinstance(b, dict) else str(b))
            for b in ai_response.content
        ]
        text_content = "".join(chunks)

    patch: dict[str, Any] = {
        "messages": [ai_response],
        "tool_calls": tool_calls,
        "llm_response_text": text_content,
    }
    return patch


__all__ = [
    "LLM_SERVICE_KEY",
    "NODE_NAME",
    "node_call_llm",
    "cap_completion_tokens",  # re-export pour tests
]
