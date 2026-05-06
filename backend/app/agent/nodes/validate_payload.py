"""F53 / T034 — Nœud ``validate_payload`` : Pydantic strict + retry.

Pour chaque ``ToolCall`` brut :
- valide les ``arguments`` contre le schéma Pydantic du tool (extra='forbid') ;
- si OK : crée un ``ValidatedToolCall`` ;
- si KO : ajoute un ``ToolMessage`` d'erreur structurée à ``state.messages``
  (le LLM verra l'erreur au prochain ``call_llm``) et incrémente
  ``state.retry_count`` ;
- si ``retry_count >= LLM_AGENT_MAX_RETRIES`` : ajoute un AgentError
  ``validation_error`` non-retriable (le graph routera vers fallback).
"""

from __future__ import annotations

import json
from typing import Any

from langchain_core.messages import ToolMessage

from app.agent.state import AgentError, AgentState, ValidatedToolCall
from app.config import get_settings
from app.orchestrator.payload_validator import format_for_llm, validate
from app.orchestrator.tool_registry import UnknownToolError, get_tool

NODE_NAME = "validate_payload"


async def node_validate_payload(state: AgentState) -> dict:
    """Valide les ``tool_calls`` non encore validés. Retourne un patch.

    Patch :
    - ``validated_calls`` : liste des nouveaux ValidatedToolCall (append)
    - ``messages`` : append de ToolMessage d'erreur si retry
    - ``retry_count`` : incrémenté si erreur
    - ``errors`` : append d'``AgentError`` si max_retries dépassé
    """
    settings = get_settings()

    # Tool calls déjà validés (par leur id)
    validated_ids = {v.id for v in state.validated_calls}
    # Tool calls dont le ToolMessage d'erreur a déjà été émis (par leur id)
    already_failed_ids = {
        e.details["tool_call_id"]
        for e in state.errors
        if e.code == "validation_error"
        and e.details
        and e.details.get("tool_call_id")
    }
    pending = [
        tc
        for tc in state.tool_calls
        if tc.id not in validated_ids and tc.id not in already_failed_ids
    ]

    if not pending:
        return {}

    new_validated: list[ValidatedToolCall] = []
    new_messages: list[ToolMessage] = []
    new_errors: list[AgentError] = []
    retry_increment = 0

    for tc in pending:
        try:
            ok, err_details = validate(tc.name, tc.arguments)
        except UnknownToolError as exc:
            new_messages.append(
                ToolMessage(
                    tool_call_id=tc.id,
                    content=json.dumps({"error": "unknown_tool", "details": str(exc)}),
                )
            )
            new_errors.append(
                AgentError(
                    node_name=NODE_NAME,
                    code="validation_error",
                    message=f"unknown_tool:{tc.name}",
                    retriable=False,
                    details={"tool_name": tc.name, "tool_call_id": tc.id},
                )
            )
            retry_increment += 1
            continue

        if ok:
            tool_def = get_tool(tc.name)
            try:
                validated_args = tool_def.schema.model_validate(tc.arguments)
            except Exception as exc:  # pragma: no cover - validate already returned ok
                new_errors.append(
                    AgentError(
                        node_name=NODE_NAME,
                        code="validation_error",
                        message=str(exc),
                        retriable=False,
                        details={"tool_name": tc.name, "tool_call_id": tc.id},
                    )
                )
                continue
            new_validated.append(
                ValidatedToolCall(
                    id=tc.id,
                    name=tc.name,
                    arguments=validated_args,
                )
            )
        else:
            # Erreur Pydantic — formater pour le LLM
            err_payload: dict[str, Any] = {
                "error": "validation_failed",
                "tool": tc.name,
                "details": [e.model_dump(mode="json") for e in err_details],
                "summary": format_for_llm(err_details),
            }
            new_messages.append(
                ToolMessage(
                    tool_call_id=tc.id,
                    content=json.dumps(err_payload, ensure_ascii=False),
                )
            )
            retry_increment += 1
            new_errors.append(
                AgentError(
                    node_name=NODE_NAME,
                    code="validation_error",
                    message=format_for_llm(err_details)[:500],
                    details={"tool_name": tc.name, "tool_call_id": tc.id},
                    retriable=state.retry_count + retry_increment <= settings.LLM_AGENT_MAX_RETRIES,
                )
            )

    patch: dict[str, Any] = {}
    if new_validated:
        patch["validated_calls"] = new_validated
    if new_messages:
        patch["messages"] = new_messages
    if retry_increment:
        patch["retry_count"] = state.retry_count + retry_increment
    if new_errors:
        patch["errors"] = new_errors
    return patch


def has_unvalidated_calls(state: AgentState) -> bool:
    """Indique si l'état contient des tool_calls non encore validés."""
    validated_ids = {v.id for v in state.validated_calls}
    return any(tc.id not in validated_ids for tc in state.tool_calls)


def has_pending_validation_failure(state: AgentState) -> bool:
    """Indique si le dernier tour a échoué la validation (retry possible)."""
    if not state.errors:
        return False
    last = state.errors[-1]
    return last.code == "validation_error" and last.retriable


__all__ = [
    "NODE_NAME",
    "has_pending_validation_failure",
    "has_unvalidated_calls",
    "node_validate_payload",
]
