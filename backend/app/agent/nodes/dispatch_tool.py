"""F53 / T035 — Nœud ``dispatch_tool`` : routage 3 voies (FR-007).

- ``SSE_ONLY``    (``ask_*``, ``show_*``)            → SSE event vers le front
- ``DB_MUTATION`` (``update_*``, ``create_*``, ``delete_*``) → exec DB + audit + SSE
- ``REINVOKE_LLM`` (``cite_source``, ``recall_history``, ``search_source``) →
  injecte le résultat en ToolMessage et signale un re-routage vers ``call_llm``

En F53 (MVP), le dispatch DB se contente de :
- valider RLS (FR-013) en restant sous la session DB de la requête ;
- créer un AuditEntry virtuel (l'écriture audit réelle dépend du handler tool
  qui sera enrichi en F54-F56) ;
- retourner ``ToolDispatchResult.status='ok'`` ;

Les handlers concrets (création projet, etc.) seront branchés au fur et à
mesure ; F53 fournit l'épine dorsale.
"""

from __future__ import annotations

import json
import logging
from typing import Any

from langchain_core.messages import ToolMessage

from app.agent.state import (
    AgentError,
    AgentState,
    DispatchCategory,
    ToolDispatchResult,
    ValidatedToolCall,
)
from app.agent.tool_factory import categorize

logger = logging.getLogger(__name__)

NODE_NAME = "dispatch_tool"


def _safe_error_message(exc: Exception) -> str:
    """Retourne un résumé d'erreur sans leak d'UUID/données sensibles."""
    msg = str(exc)
    # Tronquer pour éviter qu'un message ne contienne tout le payload
    if len(msg) > 200:
        msg = msg[:200] + "..."
    # Future : strip uuids, FK, etc. — placeholder F56
    return msg


async def _dispatch_sse_only(
    call: ValidatedToolCall,
) -> ToolDispatchResult:
    """``ask_*`` / ``show_*`` : pas d'exécution backend, juste un signal SSE.

    Le runner émet l'event SSE ``tool_invoke`` à partir du résultat.
    """
    return ToolDispatchResult(
        tool_call_id=call.id,
        tool_name=call.name,
        category=DispatchCategory.SSE_ONLY,
        status="ok",
        output={
            "tool_call_id": call.id,
            "tool_name": call.name,
            "arguments": call.arguments.model_dump(mode="json"),
        },
    )


async def _dispatch_db_mutation(
    state: AgentState,
    call: ValidatedToolCall,
) -> ToolDispatchResult:
    """``update_*`` / ``create_*`` / ``delete_*`` : exec DB sous RLS.

    F53 MVP : retourne ``ok`` sans handler concret car les handlers F17 sont
    encore en cours. F54-F56 enrichiront. L'audit est déclenché par le handler
    spécifique du tool (responsabilité F17).

    Pour les tests d'intégration F53, on peut injecter un handler via
    ``app.agent.nodes.dispatch_tool._DB_HANDLERS[name] = callable``.
    """
    handler = _DB_HANDLERS.get(call.name)
    if handler is None:
        # Aucun handler concret enregistré (cas MVP F53)
        return ToolDispatchResult(
            tool_call_id=call.id,
            tool_name=call.name,
            category=DispatchCategory.DB_MUTATION,
            status="skipped",
            output={
                "tool_call_id": call.id,
                "tool_name": call.name,
                "note": "no handler registered (MVP F53)",
            },
        )
    try:
        out = await handler(state, call)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "DB mutation failed for %s: %s", call.name, _safe_error_message(exc)
        )
        return ToolDispatchResult(
            tool_call_id=call.id,
            tool_name=call.name,
            category=DispatchCategory.DB_MUTATION,
            status="error",
            error_summary=_safe_error_message(exc),
        )
    return ToolDispatchResult(
        tool_call_id=call.id,
        tool_name=call.name,
        category=DispatchCategory.DB_MUTATION,
        status="ok",
        output=out,
        db_audit_id=None,
    )


async def _dispatch_reinvoke_llm(
    state: AgentState,
    call: ValidatedToolCall,
) -> ToolDispatchResult:
    """``cite_source`` / ``recall_history`` / ``search_source`` : re-call LLM.

    Le résultat est injecté en ``ToolMessage`` puis le graph rebascule sur
    ``call_llm``. F56-F57 enrichiront avec les vrais handlers source/memory.
    """
    handler = _REINVOKE_HANDLERS.get(call.name)
    if handler is None:
        # Stub : retourne un placeholder pour permettre la suite du flow
        return ToolDispatchResult(
            tool_call_id=call.id,
            tool_name=call.name,
            category=DispatchCategory.REINVOKE_LLM,
            status="ok",
            output={"note": f"{call.name} stub (handler enriched in F56/F57)"},
        )
    try:
        out = await handler(state, call)
    except Exception as exc:  # noqa: BLE001
        return ToolDispatchResult(
            tool_call_id=call.id,
            tool_name=call.name,
            category=DispatchCategory.REINVOKE_LLM,
            status="error",
            error_summary=_safe_error_message(exc),
        )
    return ToolDispatchResult(
        tool_call_id=call.id,
        tool_name=call.name,
        category=DispatchCategory.REINVOKE_LLM,
        status="ok",
        output=out,
    )


# Handler registries — extensibles en F54-F57
_DB_HANDLERS: dict[str, Any] = {}
_REINVOKE_HANDLERS: dict[str, Any] = {}


def register_db_handler(tool_name: str, handler: Any) -> None:
    """Enregistre un handler de mutation DB (F54+ enrichira)."""
    _DB_HANDLERS[tool_name] = handler


def register_reinvoke_handler(tool_name: str, handler: Any) -> None:
    """Enregistre un handler ``REINVOKE_LLM`` (F56/F57 enrichira)."""
    _REINVOKE_HANDLERS[tool_name] = handler


def _clear_handlers_for_tests() -> None:
    """Vide les registries (réservé aux tests)."""
    _DB_HANDLERS.clear()
    _REINVOKE_HANDLERS.clear()


# --- Nœud principal --------------------------------------------------------


async def node_dispatch_tool(state: AgentState) -> dict:
    """Dispatche tous les tool calls validés non encore dispatchés."""
    # On ne re-dispatche pas un tool_call déjà traité
    dispatched_ids = {r.tool_call_id for r in state.dispatch_results}
    pending = [v for v in state.validated_calls if v.id not in dispatched_ids]

    if not pending:
        return {}

    new_results: list[ToolDispatchResult] = []
    new_messages: list[ToolMessage] = []
    new_errors: list[AgentError] = []

    for call in pending:
        category = categorize(call.name)
        if category == DispatchCategory.SSE_ONLY:
            result = await _dispatch_sse_only(call)
        elif category == DispatchCategory.DB_MUTATION:
            result = await _dispatch_db_mutation(state, call)
        elif category == DispatchCategory.REINVOKE_LLM:
            result = await _dispatch_reinvoke_llm(state, call)
            # Injecter le résultat en ToolMessage pour réinvocation LLM
            new_messages.append(
                ToolMessage(
                    tool_call_id=call.id,
                    content=json.dumps(
                        result.output or {"status": result.status},
                        ensure_ascii=False,
                    ),
                )
            )
        else:  # pragma: no cover - exhaustive enum
            raise NotImplementedError(f"Unknown dispatch category: {category}")

        new_results.append(result)
        if result.status == "error":
            new_errors.append(
                AgentError(
                    node_name=NODE_NAME,
                    code="dispatch_error",
                    message=result.error_summary or "dispatch_failed",
                    retriable=False,
                )
            )

    patch: dict[str, Any] = {}
    if new_results:
        patch["dispatch_results"] = new_results
    if new_messages:
        patch["messages"] = new_messages
    if new_errors:
        patch["errors"] = new_errors
    if any(r.category == DispatchCategory.REINVOKE_LLM for r in new_results):
        patch["reinvoke_count"] = state.reinvoke_count + 1
    return patch


def needs_reinvoke(state: AgentState) -> bool:
    """Indique si un dispatch_result a déclenché un REINVOKE_LLM dans ce tour."""
    if not state.dispatch_results:
        return False
    # Heuristique : on regarde si le dernier batch contient du REINVOKE
    return any(
        r.category == DispatchCategory.REINVOKE_LLM and r.status == "ok"
        for r in state.dispatch_results
    )


__all__ = [
    "NODE_NAME",
    "needs_reinvoke",
    "node_dispatch_tool",
    "register_db_handler",
    "register_reinvoke_handler",
]
