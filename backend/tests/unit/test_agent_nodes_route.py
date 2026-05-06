"""F53 / T029 — Tests unitaires pour ``app/agent/nodes/route.py``."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agent.nodes.route import node_route
from app.agent.state import AgentState, ContextJson, Intent
from app.orchestrator.intent_classifier import clear_cache

pytestmark = pytest.mark.unit


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_cache()
    yield
    clear_cache()


def _state(message: str) -> AgentState:
    return AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message=message,
        context_json=ContextJson(page_route="/"),
    )


@pytest.mark.asyncio
async def test_route_classifies_mutation() -> None:
    patch = await node_route(_state("Crée un projet de panneaux solaires"))
    assert patch["intent"] == Intent.MUTATION


@pytest.mark.asyncio
async def test_route_classifies_analyse() -> None:
    patch = await node_route(_state("Compare ESG avec mon historique"))
    assert patch["intent"] == Intent.ANALYSE


@pytest.mark.asyncio
async def test_route_classifies_aide() -> None:
    patch = await node_route(_state("Comment fais-tu ?"))
    assert patch["intent"] == Intent.AIDE


@pytest.mark.asyncio
async def test_route_classifies_question_fermee() -> None:
    patch = await node_route(_state("oui"))
    assert patch["intent"] == Intent.QUESTION_FERMEE


@pytest.mark.asyncio
async def test_route_default_autre_for_unknown() -> None:
    patch = await node_route(_state("Bonjour"))
    assert patch["intent"] == Intent.AUTRE
