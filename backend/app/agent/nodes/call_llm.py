"""F53 / T033 — Nœud ``call_llm`` : invoque le LLM avec tools liés.

Responsabilités :
- charger les ``StructuredTool`` correspondants à ``state.available_tools`` ;
- bind sur le ``ChatOpenAI`` via ``bind_tools`` ;
- invoquer (synchrone via ``ainvoke`` pour ce nœud — le streaming par tokens
  est géré au niveau du runner via ``astream_events``) ;
- collecter ``tool_calls`` bruts et ``llm_response_text``.

Note : pour le MVP F53 on appelle ``ainvoke`` (réponse complète) plutôt que
``astream`` au niveau du nœud, car LangGraph fournit déjà ``astream_events``
au niveau du graph qui re-streame chunks. Cela simplifie la collecte des
tool_calls finaux (P9 — on attend la fin du tool call avant validation).
"""

from __future__ import annotations

import logging
from typing import Any

from langchain_core.messages import AIMessage

from app.agent.llm_factory import build_chat_model
from app.agent.state import AgentState, ToolCall
from app.agent.tool_factory import to_structured_tool
from app.orchestrator.tool_registry import TOOL_REGISTRY, get_tool

logger = logging.getLogger(__name__)

NODE_NAME = "call_llm"


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

    Patch retourné :
    - ``messages`` : ajoute l'``AIMessage`` (avec ``tool_calls`` éventuels)
    - ``tool_calls`` : liste des ``ToolCall`` bruts (id, name, arguments)
    - ``llm_response_text`` : contenu texte (peut être vide si tool-only)
    """
    chat_model = build_chat_model()
    structured_tools = _build_tools(state.available_tools)

    # bind_tools force le LLM à n'utiliser que ces tools (Pydantic schémas
    # sérialisés en JSON-Schema OpenAI).
    if structured_tools:
        bound = chat_model.bind_tools(structured_tools)
    else:
        bound = chat_model

    try:
        ai_response: AIMessage = await bound.ainvoke(state.messages)
    except Exception:
        logger.exception("LLM call failed")
        raise

    # Extraction des tool calls (LangChain représente les tool calls comme
    # ``message.tool_calls`` : list[{name, args, id}])
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
        # Multipart : on concatène les blocs texte
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


__all__ = ["NODE_NAME", "node_call_llm"]
