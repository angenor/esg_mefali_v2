"""F53 / T063 — Test du endpoint ``GET /health/agent`` (FR-014)."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

pytestmark = pytest.mark.integration


def _client_with_state(*, langgraph_compiled: bool, postgres_checkpointer: bool):
    """Crée un FastAPI minimal avec le router agent + state simulé."""
    from fastapi import FastAPI

    from app.agent.api import router

    app = FastAPI()
    app.include_router(router)
    app.state.agent_graph = object() if langgraph_compiled else None
    app.state.agent_checkpointer = object() if postgres_checkpointer else None
    app.state.agent_boot_duration_ms = 1234
    return TestClient(app)


def test_health_agent_response_schema(monkeypatch) -> None:
    # On mock _ping_llm pour éviter le réseau
    async def fake_ping(**kwargs):
        return True

    monkeypatch.setattr("app.agent.api._ping_llm", fake_ping)

    client = _client_with_state(langgraph_compiled=True, postgres_checkpointer=True)
    resp = client.get("/health/agent")
    assert resp.status_code == 200
    payload = resp.json()
    assert payload["ok"] is True
    assert payload["langgraph_compiled"] is True
    assert payload["postgres_checkpointer"] is True
    assert payload["llm_reachable"] is True
    assert payload["mode"] in ("langgraph", "raw")
    assert payload["boot_duration_ms"] == 1234


def test_health_agent_returns_503_when_llm_down(monkeypatch) -> None:
    async def fake_ping_down(**kwargs):
        return False

    monkeypatch.setattr("app.agent.api._ping_llm", fake_ping_down)

    client = _client_with_state(langgraph_compiled=True, postgres_checkpointer=True)
    resp = client.get("/health/agent")
    assert resp.status_code == 503
    payload = resp.json()
    assert payload["ok"] is False
    assert payload["llm_reachable"] is False
    assert "llm" in (payload.get("error") or "").lower()


def test_health_agent_returns_503_when_graph_not_compiled(monkeypatch) -> None:
    async def fake_ping(**kwargs):
        return True

    monkeypatch.setattr("app.agent.api._ping_llm", fake_ping)

    client = _client_with_state(langgraph_compiled=False, postgres_checkpointer=False)
    resp = client.get("/health/agent")
    # En mode langgraph (défaut), graph non compilé → 503
    assert resp.status_code == 503
    payload = resp.json()
    assert payload["langgraph_compiled"] is False


def test_health_agent_raw_mode_only_needs_llm(
    monkeypatch, clean_settings_cache
) -> None:
    """En mode raw, langgraph_compiled=False est OK si llm_reachable=True."""
    monkeypatch.setenv("LLM_AGENT_MODE", "raw")
    from app.config import get_settings as _gs

    _gs.cache_clear()

    async def fake_ping(**kwargs):
        return True

    monkeypatch.setattr("app.agent.api._ping_llm", fake_ping)

    client = _client_with_state(langgraph_compiled=False, postgres_checkpointer=False)
    resp = client.get("/health/agent")
    assert resp.status_code == 200, resp.text
    payload = resp.json()
    assert payload["mode"] == "raw"
    assert payload["ok"] is True
