"""Tests d'intégration : `run_agent` doit toujours persister
`agent_run.completed_at` + un `agent_run_step` par node visité.

Bugs résiduels post-PR #43 :
- Bug 1.1 — `agent_run.completed_at` reste NULL pour les runs « ok »
  (seul un sous-ensemble est complété — root cause : la fermeture du
  generator SSE par le client GC le frame avant `_safe_complete`).
- Bug 1.2 — `agent_run_step` n'est inséré pour aucun node : le pipeline
  `traced_node` (`app/agent/tracing.py`) n'est jamais wiré dans le graph.

Spec : ces tests doivent passer une fois que le runner :
1) Set `state.agent_run_id = run_id` avant `ainvoke` ;
2) Wrap chaque node avec `traced_node` (via `graph.compile_graph`) ;
3) Appelle `_safe_complete` dans un `finally` qui couvre `GeneratorExit` ;
4) Agrège `total_tokens_in/out` + set `final_node` à la complétion.
"""

from __future__ import annotations

import asyncio
from uuid import uuid4

import pytest
from langchain_core.messages import AIMessage
from sqlalchemy import text

from app.agent.graph import compile_graph
from app.agent.runner import run_agent
from app.db import get_engine_migrator
from app.orchestrator.intent_classifier import clear_cache
from app.orchestrator.tools import register_response_tools
from tests.agent_fixtures import FakeLLM, make_text_response

pytestmark = pytest.mark.integration


# ---------------------------------------------------------------------------
# Fixtures locales
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module", autouse=True)
def _register_tools() -> None:
    try:
        register_response_tools()
    except ValueError:
        pass


@pytest.fixture(autouse=True)
def _clear_caches():
    clear_cache()
    yield
    clear_cache()


def _seed_account_and_user() -> tuple:
    """Insert account + user dans la DB (BYPASSRLS via migrator)."""
    account_id = uuid4()
    user_id = uuid4()
    with get_engine_migrator().begin() as conn:
        conn.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (:id, :n, now(), now())"
            ),
            {"id": account_id, "n": f"trace-test-{account_id}"},
        )
        conn.execute(
            text(
                "INSERT INTO account_user "
                "(id, account_id, email, password_hash, role, created_at, updated_at) "
                "VALUES (:uid, :aid, :em, 'x', 'pme', now(), now())"
            ),
            {
                "uid": user_id,
                "aid": account_id,
                "em": f"trace-test-{user_id}@x.com",
            },
        )
    return account_id, user_id


def _consume_run(account_id, user_id, thread_id, **kwargs) -> list[str]:
    """Consomme tout le generator SSE et retourne la liste des lignes."""

    async def _do() -> list[str]:
        out: list[str] = []
        async for line in run_agent(
            account_id=account_id,
            user_id=user_id,
            thread_id=thread_id,
            **kwargs,
        ):
            out.append(line)
        return out

    return asyncio.get_event_loop().run_until_complete(_do())


def _fetch_run(run_id_filter_thread: str) -> dict | None:
    """Récupère le dernier `agent_run` pour ce thread_id (test scope)."""
    with get_engine_migrator().connect() as conn:
        row = (
            conn.execute(
                text(
                    "SELECT id, status, started_at, completed_at, "
                    "total_latency_ms, total_tokens_in, total_tokens_out, "
                    "final_node, error_summary, retry_count "
                    "FROM agent_run WHERE thread_id = :tid "
                    "ORDER BY started_at DESC LIMIT 1"
                ),
                {"tid": run_id_filter_thread},
            )
            .mappings()
            .fetchone()
        )
    return dict(row) if row else None


def _fetch_steps(run_id) -> list[dict]:
    with get_engine_migrator().connect() as conn:
        rows = (
            conn.execute(
                text(
                    "SELECT node_name, latency_ms, status "
                    "FROM agent_run_step WHERE run_id = :rid ORDER BY started_at"
                ),
                {"rid": run_id},
            )
            .mappings()
            .fetchall()
        )
    return [dict(r) for r in rows]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_agent_run_completed_at_set_on_success(monkeypatch) -> None:
    """Cas nominal : un tour réussi doit avoir `completed_at` non-NULL."""
    account_id, user_id = _seed_account_and_user()
    thread_id = f"{account_id}:{uuid4()}"

    fake = FakeLLM(responses=[make_text_response("Bonjour, comment puis-je aider ?")])
    monkeypatch.setattr(
        "app.agent.nodes.call_llm.build_chat_model", lambda *_a, **_k: fake
    )

    graph = compile_graph(checkpointer=None)

    lines: list[str] = []
    async for line in run_agent(
        account_id=account_id,
        user_id=user_id,
        thread_id=thread_id,
        user_message="bonjour",
        context_json={"page_route": "/"},
        compiled_graph=graph,
    ):
        lines.append(line)

    run = _fetch_run(thread_id)
    assert run is not None, "agent_run row must exist"
    assert run["completed_at"] is not None, (
        f"completed_at must be set after success (status={run['status']})"
    )
    assert run["status"] == "ok"
    assert run["total_latency_ms"] is not None and run["total_latency_ms"] >= 0


@pytest.mark.asyncio
async def test_agent_run_completed_at_set_on_error(monkeypatch) -> None:
    """Cas erreur : completed_at + status='error' + error_summary non-NULL."""
    account_id, user_id = _seed_account_and_user()
    thread_id = f"{account_id}:{uuid4()}"

    class BoomGraph:
        async def ainvoke(self, state):  # noqa: ARG002
            raise RuntimeError("explicit boom for test")

    monkeypatch.setattr(
        "app.agent.nodes.call_llm.build_chat_model", lambda *_a, **_k: FakeLLM([])
    )

    async for _line in run_agent(
        account_id=account_id,
        user_id=user_id,
        thread_id=thread_id,
        user_message="bonjour",
        context_json={"page_route": "/"},
        compiled_graph=BoomGraph(),
    ):
        pass

    run = _fetch_run(thread_id)
    assert run is not None
    assert run["completed_at"] is not None, "completed_at must be set on error too"
    assert run["status"] == "error"
    assert run["error_summary"] is not None
    assert "boom" in run["error_summary"].lower()


@pytest.mark.asyncio
async def test_agent_run_completed_at_set_on_cancellation(monkeypatch) -> None:
    """Si la consommation du SSE est annulée pendant l'exécution du graph,
    le run doit être complété (status='cancelled', completed_at non-NULL).

    Regression test pour bug 1.1 : sans le finally GeneratorExit-safe ni
    le ``except CancelledError``, completed_at restait NULL.
    """
    account_id, user_id = _seed_account_and_user()
    thread_id = f"{account_id}:{uuid4()}"

    class SlowGraph:
        async def ainvoke(self, state):  # noqa: ARG002
            await asyncio.sleep(5.0)
            return state

    monkeypatch.setattr(
        "app.agent.nodes.call_llm.build_chat_model", lambda *_a, **_k: FakeLLM([])
    )

    async def _consume():
        async for _line in run_agent(
            account_id=account_id,
            user_id=user_id,
            thread_id=thread_id,
            user_message="bonjour",
            context_json={"page_route": "/"},
            compiled_graph=SlowGraph(),
        ):
            pass

    task = asyncio.create_task(_consume())
    # Laisser le runner démarrer (start_run, INSERT agent_run)
    await asyncio.sleep(0.15)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task

    run = _fetch_run(thread_id)
    assert run is not None, "agent_run row must exist (start_run executed)"
    assert run["completed_at"] is not None, (
        "completed_at must be set even when consumer is cancelled mid-run"
    )
    # On accepte 'cancelled' (chemin CancelledError) ou 'ok' si la
    # cancellation arrive après le complete.
    assert run["status"] in {"cancelled", "ok"}


@pytest.mark.asyncio
async def test_agent_run_steps_are_persisted_per_node(monkeypatch) -> None:
    """Chaque node visité doit produire un `agent_run_step` row."""
    account_id, user_id = _seed_account_and_user()
    thread_id = f"{account_id}:{uuid4()}"

    fake = FakeLLM(responses=[make_text_response("Réponse test")])
    monkeypatch.setattr(
        "app.agent.nodes.call_llm.build_chat_model", lambda *_a, **_k: fake
    )

    graph = compile_graph(checkpointer=None)

    async for _line in run_agent(
        account_id=account_id,
        user_id=user_id,
        thread_id=thread_id,
        user_message="bonjour",
        context_json={"page_route": "/"},
        compiled_graph=graph,
    ):
        pass

    run = _fetch_run(thread_id)
    assert run is not None
    steps = _fetch_steps(run["id"])

    node_names = {s["node_name"] for s in steps}
    # Au minimum, ces 3 nodes doivent être tracés sur un tour réussi
    assert "route" in node_names, f"route step missing (got {node_names})"
    assert "build_context" in node_names, (
        f"build_context step missing (got {node_names})"
    )
    assert "call_llm" in node_names, f"call_llm step missing (got {node_names})"
    # compose_response devrait aussi être tracé en fin de chemin
    assert "compose_response" in node_names, (
        f"compose_response step missing (got {node_names})"
    )

    # latency_ms doit être set sur chaque step
    for s in steps:
        assert s["latency_ms"] is not None and s["latency_ms"] >= 0, (
            f"latency_ms missing on {s['node_name']}"
        )


@pytest.mark.asyncio
async def test_agent_run_total_tokens_aggregated(monkeypatch) -> None:
    """`total_tokens_in/out` sur agent_run doit refléter l'agrégation des
    `tokens_in/out` des steps."""
    account_id, user_id = _seed_account_and_user()
    thread_id = f"{account_id}:{uuid4()}"

    # FakeLLM avec usage_metadata pour générer des tokens trackables
    class TokenizedFake(FakeLLM):
        async def ainvoke(self, messages, **kwargs):  # noqa: ARG002
            msg = AIMessage(
                content="Bonjour avec quelques tokens",
                usage_metadata={
                    "input_tokens": 42,
                    "output_tokens": 17,
                    "total_tokens": 59,
                },
            )
            return msg

    monkeypatch.setattr(
        "app.agent.nodes.call_llm.build_chat_model",
        lambda *_a, **_k: TokenizedFake(),
    )

    graph = compile_graph(checkpointer=None)

    async for _line in run_agent(
        account_id=account_id,
        user_id=user_id,
        thread_id=thread_id,
        user_message="bonjour",
        context_json={"page_route": "/"},
        compiled_graph=graph,
    ):
        pass

    run = _fetch_run(thread_id)
    assert run is not None
    assert run["completed_at"] is not None
    # total_tokens doivent être agrégés depuis les steps (au moins call_llm)
    assert run["total_tokens_in"] is not None and run["total_tokens_in"] >= 42
    assert run["total_tokens_out"] is not None and run["total_tokens_out"] >= 17


@pytest.mark.asyncio
async def test_agent_run_final_node_set(monkeypatch) -> None:
    """`final_node` sur agent_run doit être renseigné en fin de run."""
    account_id, user_id = _seed_account_and_user()
    thread_id = f"{account_id}:{uuid4()}"

    fake = FakeLLM(responses=[make_text_response("Réponse de fin")])
    monkeypatch.setattr(
        "app.agent.nodes.call_llm.build_chat_model", lambda *_a, **_k: fake
    )

    graph = compile_graph(checkpointer=None)

    async for _line in run_agent(
        account_id=account_id,
        user_id=user_id,
        thread_id=thread_id,
        user_message="bonjour",
        context_json={"page_route": "/"},
        compiled_graph=graph,
    ):
        pass

    run = _fetch_run(thread_id)
    assert run is not None
    assert run["completed_at"] is not None
    assert run["final_node"] is not None, "final_node must be set"
    # Le chemin nominal sans tools sort par compose_response
    assert run["final_node"] == "compose_response", (
        f"expected final_node=compose_response, got {run['final_node']}"
    )
