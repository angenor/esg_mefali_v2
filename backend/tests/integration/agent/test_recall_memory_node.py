"""F54 / T075 — Test d'intégration du nœud ``recall_memory`` (FR-016).

On vérifie :
- Si la table chat_message n'existe pas / n'a pas de rows : retourne {} (no-op).
- Si déjà 2+ HumanMessage dans state.messages : no-op (idempotent).

Le test ne nécessite pas de DB ; il vérifie surtout la robustesse.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage, HumanMessage

from app.agent.nodes.recall_memory import (
    RECENT_HISTORY_CAP,
    node_recall_memory,
)
from app.agent.state import AgentState, ContextJson, compose_thread_id


def _make_state(messages: list | None = None) -> AgentState:
    aid = uuid4()
    return AgentState(
        thread_id=compose_thread_id(account_id=aid, conv_id=uuid4()),
        account_id=aid,
        user_id=uuid4(),
        user_message="Bonjour",
        context_json=ContextJson(page_route="/"),
        messages=messages or [],
    )


@pytest.mark.integration
async def test_no_history_returns_empty_dict() -> None:
    state = _make_state()
    out = await node_recall_memory(state)
    # Pas de DB / pas de rows → no-op.
    assert out in ({}, {"messages": []}) or out == {}


@pytest.mark.integration
async def test_idempotent_when_already_loaded() -> None:
    state = _make_state(
        messages=[
            HumanMessage(content="prev1"),
            AIMessage(content="answer1"),
            HumanMessage(content="prev2"),
        ]
    )
    out = await node_recall_memory(state)
    # 2+ HumanMessage présents → no-op.
    assert out == {}


@pytest.mark.integration
def test_recent_history_cap_constant() -> None:
    """FR-016 — F54 documente la frontière à 15 messages."""
    assert RECENT_HISTORY_CAP == 15
