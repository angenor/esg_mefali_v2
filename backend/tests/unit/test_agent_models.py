"""F53 — Tests unitaires pour les ORM ``app/agent/models.py``."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agent.models import AgentRun, AgentRunStep

pytestmark = pytest.mark.unit


def test_agent_run_table_name() -> None:
    assert AgentRun.__tablename__ == "agent_run"


def test_agent_run_step_table_name() -> None:
    assert AgentRunStep.__tablename__ == "agent_run_step"


def test_agent_run_has_check_constraint() -> None:
    constraints = AgentRun.__table__.constraints
    names = {c.name for c in constraints if c.name}
    assert "agent_run_thread_id_format" in names


def test_agent_run_constructor() -> None:
    run = AgentRun(
        account_id=uuid4(),
        user_id=uuid4(),
        thread_id="x:y",
    )
    assert run.thread_id == "x:y"
    # status default is set by Postgres server_default ; pas en applicatif
    assert run.id is None  # PK auto on insert


def test_agent_run_step_constructor() -> None:
    step = AgentRunStep(
        run_id=uuid4(),
        account_id=uuid4(),
        node_name="route",
    )
    assert step.node_name == "route"


def test_agent_run_columns_defined() -> None:
    cols = {c.name for c in AgentRun.__table__.columns}
    assert {
        "id",
        "account_id",
        "user_id",
        "thread_id",
        "started_at",
        "completed_at",
        "status",
        "total_latency_ms",
        "total_tokens_in",
        "total_tokens_out",
        "retry_count",
        "final_node",
        "error_summary",
    } <= cols


def test_agent_run_step_columns_defined() -> None:
    cols = {c.name for c in AgentRunStep.__table__.columns}
    assert {
        "id",
        "run_id",
        "account_id",
        "node_name",
        "started_at",
        "latency_ms",
        "tokens_in",
        "tokens_out",
        "tool_calls_count",
        "status",
        "error",
    } <= cols
