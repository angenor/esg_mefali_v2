"""F53 / T025 — E2E backend : création projet via tool calls validés (US1 / SC-001).

Scénario :
- Un run agent reçoit « Crée un projet de panneaux solaires de 50 kWc »
- Le fakellm retourne séquentiellement : ``ask_qcu`` (montant) → texte final
- On vérifie : SSE events (``tool_invoke``, ``done``), absence d'erreur.

Marker : ``@pytest.mark.e2e``
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agent.graph import compile_graph
from app.agent.runner import run_agent
from app.agent.state import AgentState, ContextJson
from app.orchestrator.intent_classifier import clear_cache
from app.orchestrator.tools import register_response_tools
from app.orchestrator.tools.mutations import register_mutation_tools
from tests.agent_fixtures import (
    FakeLLM,
    make_text_response,
    make_tool_call_response,
)

pytestmark = [pytest.mark.integration]


@pytest.fixture(scope="module", autouse=True)
def _register_tools() -> None:
    try:
        register_response_tools()
    except ValueError:
        pass
    try:
        register_mutation_tools()
    except ValueError:
        pass


@pytest.fixture(autouse=True)
def _clear_intent_cache():
    clear_cache()
    yield
    clear_cache()


def _make_account_thread():
    account_id = uuid4()
    conv_id = uuid4()
    thread_id = f"{account_id}:{conv_id}"
    return account_id, uuid4(), thread_id


# ---------------------------------------------------------------------------
# SC-001 : ask_qcu dans le flow de création projet → SSE events corrects
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_e2e_create_project_via_tool_calls(monkeypatch) -> None:
    """E2E : flow ask_qcu → done — SSE events tool_invoke + done présents."""
    account_id, user_id, thread_id = _make_account_thread()

    fake = FakeLLM(
        responses=[
            make_tool_call_response(
                tool_name="ask_qcu",
                tool_args={
                    "question": "Quel est le montant prévu pour votre projet solaire ?",
                    "options": [
                        {"value": "lt10M", "label": "Moins de 10M FCFA"},
                        {"value": "10_50M", "label": "Entre 10M et 50M FCFA"},
                        {"value": "gt50M", "label": "Plus de 50M FCFA"},
                    ],
                },
            ),
        ]
    )
    monkeypatch.setattr("app.agent.nodes.call_llm.build_chat_model", lambda *_a, **_k: fake)

    graph = compile_graph(checkpointer=None)

    sse_lines: list[str] = []
    async for line in run_agent(
        account_id=account_id,
        user_id=user_id,
        thread_id=thread_id,
        user_message="Crée un projet de panneaux solaires de 50 kWc",
        context_json={"page_route": "/profil/projets"},
        compiled_graph=graph,
    ):
        sse_lines.append(line)

    # Le runner yield des strings SSE multi-lignes → les aplatir
    flat_lines: list[str] = []
    for chunk in sse_lines:
        flat_lines.extend(chunk.splitlines())

    # Reconstruire les event types
    event_types = [
        line.removeprefix("event:").strip()
        for line in flat_lines
        if line.startswith("event:")
    ]

    # Le flow doit émettre tool_invoke (ask_qcu est SSE_ONLY) puis done
    assert "tool_invoke" in event_types, f"tool_invoke manquant dans {event_types}"
    assert "done" in event_types, f"done manquant dans {event_types}"
    # Aucune erreur fatale ne doit être émise
    assert "error" not in event_types, f"event error inattendu dans {event_types}"


@pytest.mark.asyncio
async def test_e2e_create_project_flow_no_sse_errors(monkeypatch) -> None:
    """E2E : flow texte simple → done sans event error."""
    account_id, user_id, thread_id = _make_account_thread()

    fake = FakeLLM(
        responses=[
            make_text_response(
                "Je vais vous aider à créer votre projet de panneaux solaires. "
                "Quel est le montant de financement recherché ?"
            ),
        ]
    )
    monkeypatch.setattr("app.agent.nodes.call_llm.build_chat_model", lambda *_a, **_k: fake)

    graph = compile_graph(checkpointer=None)

    sse_lines: list[str] = []
    async for line in run_agent(
        account_id=account_id,
        user_id=user_id,
        thread_id=thread_id,
        user_message="Crée un projet de panneaux solaires de 50 kWc",
        context_json={"page_route": "/profil/projets"},
        compiled_graph=graph,
    ):
        sse_lines.append(line)

    flat_lines: list[str] = []
    for chunk in sse_lines:
        flat_lines.extend(chunk.splitlines())

    event_types = [
        line.removeprefix("event:").strip()
        for line in flat_lines
        if line.startswith("event:")
    ]

    # Un texte direct : token + done, pas d'erreur
    assert "done" in event_types, f"done manquant dans {event_types}"
    assert "error" not in event_types, f"event error inattendu dans {event_types}"


@pytest.mark.asyncio
async def test_e2e_create_project_sse_ask_qcu_tool_invoke_payload(monkeypatch) -> None:
    """E2E : le payload SSE du tool_invoke doit contenir tool_name=ask_qcu."""
    account_id, user_id, thread_id = _make_account_thread()

    fake = FakeLLM(
        responses=[
            make_tool_call_response(
                tool_name="ask_qcu",
                tool_args={
                    "question": "Quel montant ?",
                    "options": [
                        {"value": "a", "label": "25M FCFA"},
                        {"value": "b", "label": "50M FCFA"},
                    ],
                },
            ),
        ]
    )
    monkeypatch.setattr("app.agent.nodes.call_llm.build_chat_model", lambda *_a, **_k: fake)

    graph = compile_graph(checkpointer=None)

    import json

    sse_chunks: list[str] = []
    async for chunk in run_agent(
        account_id=account_id,
        user_id=user_id,
        thread_id=thread_id,
        user_message="Aide-moi à créer un projet solaire",
        context_json={"page_route": "/profil/projets"},
        compiled_graph=graph,
    ):
        sse_chunks.append(chunk)

    # Aplatir les chunks multi-lignes
    flat_lines: list[str] = []
    for chunk in sse_chunks:
        flat_lines.extend(chunk.splitlines())

    sse_data_lines: list[dict] = []
    cur_event: str | None = None
    for line in flat_lines:
        stripped = line.strip()
        if stripped.startswith("event:"):
            cur_event = stripped.removeprefix("event:").strip()
        elif stripped.startswith("data:") and cur_event == "tool_invoke":
            raw = stripped.removeprefix("data:").strip()
            try:
                sse_data_lines.append(json.loads(raw))
            except json.JSONDecodeError:
                pass
            cur_event = None

    assert sse_data_lines, "Aucun payload tool_invoke reçu"
    payload = sse_data_lines[0]
    assert payload.get("tool_name") == "ask_qcu", f"tool_name inattendu: {payload}"
