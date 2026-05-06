"""F55 / T060 — Integration test ASK/SHOW dispatch.

Vérifie qu'ASK et SHOW ne touchent PAS la DB et retournent kind='frontend_event'.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text

from app.agent.dispatcher import dispatch
from app.agent.state import (
    AgentState,
    ContextJson,
    ToolCategory,
    ValidatedToolCall,
)
from app.orchestrator.tool_registry import (
    TOOL_REGISTRY,
    reset_registry,
    tool,
)
from tests.conftest import DB_AVAILABLE

pytestmark = pytest.mark.integration


class _AskUnitArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    question: str = Field(min_length=1)


class _ShowUnitArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    title: str
    series: list[float] = Field(default_factory=list)


@pytest.fixture(autouse=True)
def _registry_iso():
    backup = dict(TOOL_REGISTRY)
    reset_registry()
    yield
    reset_registry()
    TOOL_REGISTRY.update(backup)


def _make_state():
    return AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message="hi",
        context_json=ContextJson(page_route="/chat"),
    )


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
@pytest.mark.asyncio
async def test_dispatch_ask_no_db_write(db_engine):
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    tool(
        name="ask_qcu_int_test",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_AskUnitArgs,
        category=ToolCategory.ASK,
    )
    call = ValidatedToolCall(
        id="c1",
        name="ask_qcu_int_test",
        arguments=_AskUnitArgs(question="Quelle forme juridique?"),
    )
    state = _make_state()
    with Session() as db:
        # Snapshot tool_call_log count avant
        count_before = db.execute(
            text("SELECT COUNT(*) FROM tool_call_log")
        ).scalar_one()

        result = await dispatch(call, state, db)
        assert result.kind == "frontend_event"
        assert result.status == "ok"
        assert result.output["arguments"] == {"question": "Quelle forme juridique?"}

        count_after = db.execute(
            text("SELECT COUNT(*) FROM tool_call_log")
        ).scalar_one()
        # ASK ne crée AUCUN log dispatch
        assert count_after == count_before


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
@pytest.mark.asyncio
async def test_dispatch_show_no_db_write(db_engine):
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    tool(
        name="show_radar_test",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_ShowUnitArgs,
        category=ToolCategory.SHOW,
    )
    call = ValidatedToolCall(
        id="c2",
        name="show_radar_test",
        arguments=_ShowUnitArgs(title="Score ESG", series=[0.5, 0.7, 0.6]),
    )
    state = _make_state()
    with Session() as db:
        count_before = db.execute(
            text("SELECT COUNT(*) FROM tool_call_log")
        ).scalar_one()

        result = await dispatch(call, state, db)
        assert result.kind == "frontend_event"
        assert result.status == "ok"
        assert result.output["category"] == "show"

        count_after = db.execute(
            text("SELECT COUNT(*) FROM tool_call_log")
        ).scalar_one()
        assert count_after == count_before
