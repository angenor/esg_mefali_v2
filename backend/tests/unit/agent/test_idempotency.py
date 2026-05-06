"""F55 / T103 — Unit tests idempotency utilities."""

from __future__ import annotations

from uuid import UUID, uuid4

import pytest

from app.agent.idempotency import compute_idempotency_key, reconstruct_result

pytestmark = pytest.mark.unit


def test_compute_idempotency_deterministic():
    aid = UUID("11111111-1111-1111-1111-111111111111")
    rid = UUID("22222222-2222-2222-2222-222222222222")
    k1 = compute_idempotency_key(aid, rid, "call_x")
    k2 = compute_idempotency_key(aid, rid, "call_x")
    assert k1 == k2
    assert len(k1) == 32


def test_compute_idempotency_distinct_for_distinct_inputs():
    aid = uuid4()
    rid = uuid4()
    k1 = compute_idempotency_key(aid, rid, "a")
    k2 = compute_idempotency_key(aid, rid, "b")
    assert k1 != k2


def test_compute_idempotency_handles_no_run():
    aid = uuid4()
    k = compute_idempotency_key(aid, None, "call_y")
    assert len(k) == 32


def test_reconstruct_result_mutation_kind():
    row = {
        "id": uuid4(),
        "tool_call_id": "call_1",
        "tool_name": "update_company_profile",
        "status": "ok",
        "dispatch_result_kind": "mutation_result",
        "output_json": {"snapshot": {"id": "x"}},
        "error_summary": None,
        "entity_type": "entreprise",
        "entity_id": uuid4(),
        "audit_log_id": None,
        "is_dry_run": False,
    }
    result = reconstruct_result(row)
    assert result.kind == "mutation_result"
    assert result.tool_name == "update_company_profile"
    assert result.status == "ok"
    assert result.entity_type == "entreprise"


def test_reconstruct_result_frontend_event_kind():
    row = {
        "id": uuid4(),
        "tool_call_id": "call_2",
        "tool_name": "ask_qcu",
        "status": "ok",
        "dispatch_result_kind": "frontend_event",
        "output_json": {"arguments": {"q": "?"}},
        "error_summary": None,
        "entity_type": None,
        "entity_id": None,
        "audit_log_id": None,
        "is_dry_run": False,
    }
    result = reconstruct_result(row)
    assert result.kind == "frontend_event"


def test_reconstruct_result_handles_null_kind():
    row = {
        "id": uuid4(),
        "tool_call_id": "call_3",
        "tool_name": "x",
        "status": "ok",
        "dispatch_result_kind": None,
        "output_json": None,
        "error_summary": None,
        "entity_type": None,
        "entity_id": None,
        "audit_log_id": None,
        "is_dry_run": False,
    }
    result = reconstruct_result(row)
    assert result.tool_name == "x"
