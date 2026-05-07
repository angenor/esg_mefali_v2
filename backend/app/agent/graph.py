"""F53 / T037 — Construction du ``StateGraph[AgentState]`` LangGraph.

Topologie (FR-001, FR-007) :

    START
      │
      ▼
    route ──► build_context ──► recall_memory ──► select_tools ──► call_llm
                                                                     │
                                                                     ▼
                                                            validate_payload
                                                                ├─►(retry max)─► compose_response ──► END
                                                                ├─►(retry possible)─► call_llm
                                                                └─►(ok)─► dispatch_tool
                                                                              ├─►(REINVOKE_LLM)─► call_llm
                                                                              └─►(otherwise)─► compose_response ──► END

Edges conditionnels :
- ``validate_payload → call_llm`` si ``retry_count < MAX`` et erreurs
- ``validate_payload → dispatch_tool`` si tous validés
- ``validate_payload → compose_response`` si max retries dépassés
- ``dispatch_tool → call_llm`` si REINVOKE_LLM exécuté ET reinvoke_count < MAX
- ``dispatch_tool → compose_response`` sinon

Tracing (F53/T072 + post-PR43 fix) :

Chaque nœud est enveloppé par :func:`_make_traced_node` qui ouvre une
session ``migrator`` (BYPASSRLS) le temps du nœud, mesure la latence,
extrait les ``usage_metadata`` éventuelles d'un ``AIMessage`` retourné par
``call_llm`` et écrit un row ``agent_run_step``. Le wrapping est
inactif (no-op) si ``state.agent_run_id`` est ``None`` (cas test sans
runner) ou si ``LLM_AGENT_TRACE='off'``.
"""

from __future__ import annotations

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph

from app.agent.nodes.build_context import NODE_NAME as N_BUILD
from app.agent.nodes.build_context import node_build_context
from app.agent.nodes.call_llm import NODE_NAME as N_LLM
from app.agent.nodes.call_llm import node_call_llm
from app.agent.nodes.compose_response import NODE_NAME as N_COMPOSE
from app.agent.nodes.compose_response import node_compose_response
from app.agent.nodes.dispatch_tool import NODE_NAME as N_DISPATCH
from app.agent.nodes.dispatch_tool import node_dispatch_tool
from app.agent.nodes.recall_memory import NODE_NAME as N_RECALL
from app.agent.nodes.recall_memory import node_recall_memory
from app.agent.nodes.route import NODE_NAME as N_ROUTE
from app.agent.nodes.route import node_route
from app.agent.nodes.select_tools import NODE_NAME as N_SELECT
from app.agent.nodes.select_tools import node_select_tools
from app.agent.nodes.validate_payload import (
    NODE_NAME as N_VALIDATE,
)
from app.agent.nodes.validate_payload import (
    node_validate_payload,
)
from app.agent.state import AgentState, DispatchCategory
from app.agent.tracing import TraceContext, get_trace_mode, traced_node
from app.config import get_settings

logger = logging.getLogger(__name__)

# Plafond anti-boucle infinie sur REINVOKE_LLM (FR Edge cases)
_MAX_REINVOKE = 3


def _ids_failed(state: AgentState) -> set[str]:
    """Ids des tool_calls qui ont déjà raté la validation.

    On les ignore au prochain passage de validate (le LLM est censé re-émettre
    un nouvel id corrigé après avoir lu le ToolMessage d'erreur).
    """
    return {
        e.details["tool_call_id"]
        for e in state.errors
        if e.code == "validation_error"
        and e.details
        and e.details.get("tool_call_id")
    }


def _has_pending_validation(state: AgentState) -> bool:
    """True si un tool_call n'a pas encore été validé NI marqué failed."""
    processed = {v.id for v in state.validated_calls} | _ids_failed(state)
    return any(tc.id not in processed for tc in state.tool_calls)


def _has_undispatched_validated(state: AgentState) -> bool:
    """True si au moins un validated_call n'a pas encore été dispatché."""
    dispatched_ids = {r.tool_call_id for r in state.dispatch_results}
    return any(v.id not in dispatched_ids for v in state.validated_calls)


def _route_after_call_llm(state: AgentState) -> str:
    """Si le LLM a émis des tool_calls à valider → validate, sinon compose."""
    if _has_pending_validation(state):
        return N_VALIDATE
    return N_COMPOSE


def _route_after_validate(state: AgentState) -> str:
    """Branchement post-validation (FR-006).

    - Si au moins un validated non dispatché → dispatch_tool
    - Si on a eu une erreur de validation ET retry_count <= MAX → call_llm
      (le LLM doit re-émettre un nouveau tool_call corrigé après avoir vu
      le ToolMessage d'erreur)
    - Sinon → compose_response (fallback ou fin de tour)
    """
    settings = get_settings()
    if _has_undispatched_validated(state):
        return N_DISPATCH

    # Pas de validated_calls : soit erreur, soit rien à dispatcher.
    if state.retry_count > 0 and state.retry_count <= settings.LLM_AGENT_MAX_RETRIES:
        # Erreur de validation récupérable → re-call LLM
        return N_LLM
    return N_COMPOSE


def _route_after_dispatch(state: AgentState) -> str:
    """Branchement post-dispatch (FR-007).

    - Si un dispatch a déclenché REINVOKE_LLM ET reinvoke_count < MAX → call_llm
    - Sinon → compose_response
    """
    if state.reinvoke_count >= _MAX_REINVOKE:
        return N_COMPOSE
    last_batch_reinvoke = any(
        r.category == DispatchCategory.REINVOKE_LLM and r.status == "ok"
        for r in state.dispatch_results
    )
    # On veut router vers call_llm UNIQUEMENT si les REINVOKE_LLM viennent
    # d'être effectués (cas de boucle d'analyse sourcée). Un compteur dédié
    # incrementé par dispatch_tool (reinvoke_count) sert de garde-fou.
    if last_batch_reinvoke and state.reinvoke_count > 0 and state.reinvoke_count < _MAX_REINVOKE:
        return N_LLM
    return N_COMPOSE


def _route_after_compose(state: AgentState) -> str:
    """F56 — Branchement post-compose_response (FR-008/FR-009).

    - Si ``sourcing_decision == 'retry'`` ET on n'a pas encore consommé le
      retry unique (``final_text`` reste vide après le compose) → re-appel
      ``call_llm``. Le compteur ``sourcing_retry_count`` est plafonné à 1
      par le ``_max_reducer``.
    - Sinon → END.
    """
    if (
        state.sourcing_decision == "retry"
        and not state.final_text
        and state.sourcing_retry_count <= 1
    ):
        return N_LLM
    return END


_NodeFn = Callable[[AgentState], Awaitable[dict[str, Any]]]


def _extract_usage_from_patch(patch: Any) -> tuple[int | None, int | None]:
    """Récupère les ``input_tokens``/``output_tokens`` d'un patch de nœud.

    Le ``call_llm`` retourne un patch ``{"messages": [AIMessage]}``. Si
    l'``AIMessage`` expose ``usage_metadata`` (LangChain >= 0.2), on en tire
    les compteurs pour les écrire dans ``agent_run_step``.
    """
    if not isinstance(patch, dict):
        return None, None
    messages = patch.get("messages") or []
    tokens_in: int | None = None
    tokens_out: int | None = None
    for msg in messages:
        if not isinstance(msg, AIMessage):
            continue
        usage = getattr(msg, "usage_metadata", None)
        if not usage:
            continue
        ti = usage.get("input_tokens") if isinstance(usage, dict) else None
        to = usage.get("output_tokens") if isinstance(usage, dict) else None
        if ti is not None:
            tokens_in = (tokens_in or 0) + int(ti)
        if to is not None:
            tokens_out = (tokens_out or 0) + int(to)
    return tokens_in, tokens_out


def _open_trace_session():
    """Ouvre une session SQLAlchemy bind sur l'engine migrator (BYPASSRLS)."""
    from sqlalchemy.orm import Session

    from app.db import get_engine_migrator

    return Session(bind=get_engine_migrator())


def _make_traced_node(node_fn: _NodeFn, node_name: str) -> _NodeFn:
    """Enveloppe ``node_fn`` avec ``traced_node`` pour persister un step.

    No-op si ``state.agent_run_id is None`` ou si le mode tracing est
    ``off``. Toute exception levée par ``node_fn`` est propagée intacte
    au graph (pour préserver les chemins ``except`` du runner) ; le step
    est néanmoins enregistré avec ``status='error'`` via ``traced_node``.
    """

    async def _wrapped(state: AgentState) -> dict[str, Any]:
        run_id = getattr(state, "agent_run_id", None)
        trace_mode = get_trace_mode()

        # Fast path : pas de tracing → exécution directe.
        if run_id is None or trace_mode == "off":
            return await node_fn(state)

        trace_session = None
        try:
            trace_session = _open_trace_session()
            # Purge défensive (pool peut retourner une connection sale).
            trace_session.rollback()
            ctx = TraceContext(
                run_id=run_id,
                account_id=state.account_id,
                session=trace_session,
                trace_mode=trace_mode,
            )
            async with traced_node(ctx, node_name=node_name) as counters:
                result = await node_fn(state)
                # Capture tokens si le patch contient un AIMessage avec
                # usage_metadata (cas typique : ``call_llm``).
                ti, to = _extract_usage_from_patch(result)
                if ti is not None:
                    counters.tokens_in = ti
                if to is not None:
                    counters.tokens_out = to
                # Compte les tool_calls éventuels présents dans le patch.
                if isinstance(result, dict) and isinstance(
                    result.get("tool_calls"), list
                ):
                    counters.tool_calls_count = len(result["tool_calls"])
            trace_session.commit()
            return result
        except Exception:
            # ``traced_node`` a déjà loggé le step en status='error' avant
            # de re-raise via le finally.
            if trace_session is not None:
                try:
                    trace_session.commit()
                except Exception:  # noqa: BLE001
                    trace_session.rollback()
            raise
        finally:
            if trace_session is not None:
                try:
                    trace_session.close()
                except Exception:  # noqa: BLE001
                    pass

    _wrapped.__name__ = f"traced_{node_name}"
    return _wrapped


def build_graph() -> StateGraph:
    """Assemble le ``StateGraph[AgentState]`` (non compilé).

    Le compileur ajoute le checkpointer ; la compilation est faite par
    ``compile_agent_graph`` au boot. Chaque nœud est enveloppé par
    :func:`_make_traced_node` pour persister un ``agent_run_step``.
    """
    g: StateGraph[AgentState] = StateGraph(AgentState)

    g.add_node(N_ROUTE, _make_traced_node(node_route, N_ROUTE))
    g.add_node(N_BUILD, _make_traced_node(node_build_context, N_BUILD))
    g.add_node(N_RECALL, _make_traced_node(node_recall_memory, N_RECALL))
    g.add_node(N_SELECT, _make_traced_node(node_select_tools, N_SELECT))
    g.add_node(N_LLM, _make_traced_node(node_call_llm, N_LLM))
    g.add_node(N_VALIDATE, _make_traced_node(node_validate_payload, N_VALIDATE))
    g.add_node(N_DISPATCH, _make_traced_node(node_dispatch_tool, N_DISPATCH))
    g.add_node(N_COMPOSE, _make_traced_node(node_compose_response, N_COMPOSE))

    # Edges linéaires
    g.add_edge(START, N_ROUTE)
    g.add_edge(N_ROUTE, N_BUILD)
    g.add_edge(N_BUILD, N_RECALL)
    g.add_edge(N_RECALL, N_SELECT)
    g.add_edge(N_SELECT, N_LLM)

    # Edges conditionnels
    g.add_conditional_edges(
        N_LLM,
        _route_after_call_llm,
        {N_VALIDATE: N_VALIDATE, N_COMPOSE: N_COMPOSE},
    )
    g.add_conditional_edges(
        N_VALIDATE,
        _route_after_validate,
        {N_LLM: N_LLM, N_DISPATCH: N_DISPATCH, N_COMPOSE: N_COMPOSE},
    )
    g.add_conditional_edges(
        N_DISPATCH,
        _route_after_dispatch,
        {N_LLM: N_LLM, N_COMPOSE: N_COMPOSE},
    )
    # F56 — compose_response peut demander un retry sourçage en mode strict
    # (au plus 1 par tour ; cf. FR-009). Le routeur `_route_after_compose`
    # ré-appelle `call_llm` si `sourcing_decision == 'retry'`, sinon END.
    g.add_conditional_edges(
        N_COMPOSE,
        _route_after_compose,
        {N_LLM: N_LLM, END: END},
    )

    return g


def compile_graph(checkpointer: Any | None = None):
    """Compile le graph ; checkpointer optionnel pour tests."""
    g = build_graph()
    if checkpointer is not None:
        return g.compile(checkpointer=checkpointer)
    return g.compile()


__all__ = [
    "build_graph",
    "compile_graph",
]
