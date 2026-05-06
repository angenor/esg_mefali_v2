"""F53 / T031 — Nœud ``recall_memory`` : injecte la mémoire conversationnelle.

MVP F53 : no-op placeholder. F18 a déjà ``execute_recall_history`` mais son
appel direct dépend d'une session DB et est mieux placé dans ``dispatch_tool``
quand le LLM choisit explicitement le tool ``recall_history``.

Ce nœud reste présent dans le graph pour permettre à F57 (memory RAG) d'y
brancher la récupération contextuelle automatique. En F53, il passe.
"""

from __future__ import annotations

from app.agent.state import AgentState

NODE_NAME = "recall_memory"


async def node_recall_memory(state: AgentState) -> dict:
    """No-op MVP F53. F57 enrichira avec un recall pgvector contextuel."""
    return {}


__all__ = ["NODE_NAME", "node_recall_memory"]
