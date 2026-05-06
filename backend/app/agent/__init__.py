"""F53 — Agent LangGraph Core.

Module d'orchestration : remplace le proxy LLM brut (F13) par une machine
d'état StateGraph qui orchestre F14 (classifier/validator/retry),
F15-F17 (tools), F18 (memory), F19-F21 (skills) en un pipeline cohérent.

Exports principaux :

- ``compile_agent_graph()`` : compile et retourne le graph + checkpointer (boot).
- ``run_agent(...)`` : runner asynchrone qui produit un AsyncIterator[SseEvent].
- ``AgentState`` : type Pydantic v2 du state circulant dans le graph.

Lecture conseillée : ``specs/053-agent-langgraph-core/{spec,plan,data-model}.md``.
"""

from __future__ import annotations

from app.agent.state import (
    AgentError,
    AgentState,
    ContextJson,
    DispatchCategory,
    Intent,
    ToolCall,
    ToolDispatchResult,
    ValidatedToolCall,
)

__all__ = [
    "AgentError",
    "AgentState",
    "ContextJson",
    "DispatchCategory",
    "Intent",
    "ToolCall",
    "ToolDispatchResult",
    "ValidatedToolCall",
]
