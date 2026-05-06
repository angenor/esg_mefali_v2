"""F57 — Tests unit pour ``app/agent/memory/__init__.py`` (install hook)
et ``app/agent/memory/models.py`` (ORM smoke tests).
"""

from __future__ import annotations

import uuid

import pytest

import app.agent.memory as agent_memory_pkg
from app.agent.memory.models import AgentEntityMemory, RecallLog

pytestmark = pytest.mark.unit


def test_install_post_mutation_hook_idempotent(monkeypatch) -> None:
    """install_post_mutation_hook ne doit pas dupliquer les hooks."""
    from app.agent import dispatcher

    # Reset le flag interne et les hooks pour partir propre
    agent_memory_pkg._reset_hook_installed_flag()
    dispatcher.reset_hooks()

    agent_memory_pkg.install_post_mutation_hook()
    after_count_1 = len(dispatcher._HOOKS.after)
    before_count_1 = len(dispatcher._HOOKS.before)
    assert after_count_1 == 1
    assert before_count_1 == 1

    # Second call → no-op (le flag bloque)
    agent_memory_pkg.install_post_mutation_hook()
    assert len(dispatcher._HOOKS.after) == after_count_1
    assert len(dispatcher._HOOKS.before) == before_count_1

    # Cleanup
    agent_memory_pkg._reset_hook_installed_flag()
    dispatcher.reset_hooks()


def test_agent_entity_memory_orm_basic_attrs() -> None:
    """ORM smoke : on peut instancier (sans DB) avec les bons champs."""
    aid = uuid.uuid4()
    eid = uuid.uuid4()
    obj = AgentEntityMemory(
        account_id=aid,
        entity_type="Entreprise",
        entity_id=eid,
        summary="bullet 1",
    )
    assert obj.account_id == aid
    assert obj.entity_type == "Entreprise"
    assert obj.entity_id == eid


def test_recall_log_orm_basic_attrs() -> None:
    aid = uuid.uuid4()
    tid = uuid.uuid4()
    obj = RecallLog(
        account_id=aid,
        thread_id=tid,
        recall_type="auto",
        query_hash="abcd",
        top_k=3,
        top_scores=[],
        latency_ms=42,
    )
    assert obj.recall_type == "auto"
    assert obj.top_k == 3
    assert obj.latency_ms == 42


def test_models_table_names() -> None:
    """Sanity : __tablename__ aligned with migration."""
    assert AgentEntityMemory.__tablename__ == "agent_entity_memory"
    assert RecallLog.__tablename__ == "recall_log"
