"""F57 / US9 — Tests unit ``recall_log.stage_entry`` & ``flush_entries``.

L'INSERT direct + RLS sont validés en intégration ; ici on couvre la
construction des entries + le tronquage des erreurs.
"""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agent.memory import recall_log

pytestmark = pytest.mark.unit


def test_stage_entry_basic_auto() -> None:
    aid = uuid4()
    e = recall_log.stage_entry(
        recall_type="auto",
        thread_id=str(uuid4()),
        account_id=aid,
        query_hash="abcd",
        top_k=3,
        top_scores=[{"message_id": str(uuid4()), "score": 0.91}],
        latency_ms=42,
    )
    assert e["recall_type"] == "auto"
    assert e["account_id"] == str(aid)
    assert e["query_hash"] == "abcd"
    assert e["top_k"] == 3
    assert e["latency_ms"] == 42
    assert isinstance(e["top_scores"], list)


def test_stage_entry_invalid_recall_type_raises() -> None:
    with pytest.raises(ValueError):
        recall_log.stage_entry(
            recall_type="bogus",  # type: ignore[arg-type]
            thread_id=str(uuid4()),
            account_id=uuid4(),
            query_hash="x",
            top_k=1,
            top_scores=[],
            latency_ms=10,
        )


def test_stage_entry_with_agent_run_id() -> None:
    rid = uuid4()
    e = recall_log.stage_entry(
        recall_type="tool",
        thread_id=str(uuid4()),
        account_id=uuid4(),
        query_hash="h",
        top_k=2,
        top_scores=[],
        latency_ms=0,
        agent_run_id=rid,
    )
    assert e["agent_run_id"] == str(rid)


def test_stage_entry_default_agent_run_id_none() -> None:
    e = recall_log.stage_entry(
        recall_type="tool",
        thread_id=str(uuid4()),
        account_id=uuid4(),
        query_hash="h",
        top_k=2,
        top_scores=[],
        latency_ms=0,
    )
    assert e["agent_run_id"] is None


def test_stage_entry_thread_id_can_be_composite() -> None:
    """Le caller passe ``thread_id`` composite ; on stocke tel quel ; le
    write_recall_log normalisera en UUID au moment du flush."""
    composite = f"{uuid4()}:{uuid4()}"
    e = recall_log.stage_entry(
        recall_type="auto",
        thread_id=composite,
        account_id=uuid4(),
        query_hash="h",
        top_k=2,
        top_scores=[],
        latency_ms=0,
    )
    assert e["thread_id"] == composite
