"""F55 / T080 — Integration test confirmation flow (US3).

1. delete_* avec requires_confirmation=True ET pas de confirm → kind='frontend_event',
   status='pending_confirmation', pending stocké.
2. Tour suivant avec confirm=False (no) → status='cancelled_by_user'.
3. Tour suivant avec confirm=True (yes) → call exécuté.
"""

from __future__ import annotations

import json
from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from app.agent.dispatcher import dispatch
from app.agent.mutation_handlers import (
    mutation_handler,
    reset_mutation_handlers,
)
from app.agent.rate_limit import InMemoryRateLimitStore, set_rate_store
from app.agent.state import (
    AgentState,
    ContextJson,
    MutationResult,
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


class _DeleteArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    entity_id: str
    confirm: bool = False


@pytest.fixture(autouse=True)
def _isolation():
    backup = dict(TOOL_REGISTRY)
    reset_registry()
    reset_mutation_handlers()
    set_rate_store(InMemoryRateLimitStore())
    yield
    reset_registry()
    reset_mutation_handlers()
    set_rate_store(None)
    TOOL_REGISTRY.update(backup)


def _bootstrap_account_and_run(db) -> tuple[str, str, str]:
    acc_id = db.execute(
        text(
            "INSERT INTO account (id, name, created_at, updated_at) "
            "VALUES (gen_random_uuid(), 'Conf', now(), now()) RETURNING id"
        )
    ).scalar_one()
    usr_id = db.execute(
        text(
            "INSERT INTO account_user (id, account_id, email, password_hash, "
            "role, created_at, updated_at) "
            "VALUES (gen_random_uuid(), :a, :e, 'h', 'pme', now(), now()) RETURNING id"
        ),
        {"a": acc_id, "e": f"conf_{uuid4()}@x.com"},
    ).scalar_one()
    # Bootstrap agent_run (status enum: ok/error/timeout/cancelled)
    run_id = db.execute(
        text(
            "INSERT INTO agent_run (id, account_id, user_id, thread_id, "
            "status, started_at) "
            "VALUES (gen_random_uuid(), :a, :u, :t, 'ok', now()) "
            "RETURNING id"
        ),
        {
            "a": acc_id,
            "u": usr_id,
            "t": f"{acc_id}:{uuid4()}",
        },
    ).scalar_one()
    db.commit()
    db.execute(text(f"SET LOCAL \"app.current_account_id\" = '{acc_id}'"))
    db.execute(text(f"SET LOCAL \"app.current_user_id\" = '{usr_id}'"))
    return str(acc_id), str(usr_id), str(run_id)


def _setup_delete_tool():
    tool(
        name="delete_test_thing",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_DeleteArgs,
        category=ToolCategory.MUTATION,
    )

    invocations = {"count": 0}

    @mutation_handler("delete_test_thing", requires_confirmation=True)
    async def _h(args, ctx):
        invocations["count"] += 1
        return MutationResult(
            entity_type="thing",
            entity_id=uuid4(),
            fields_updated=["deleted_at"],
            snapshot={"deleted": True},
        )

    return invocations


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
@pytest.mark.asyncio
async def test_first_delete_call_returns_pending_confirmation(db_engine):
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    invocations = _setup_delete_tool()
    with Session() as db:
        acc_id, usr_id, run_id = _bootstrap_account_and_run(db)
        from uuid import UUID as _UUID

        call = ValidatedToolCall(
            id=f"cdel_{uuid4().hex}",
            name="delete_test_thing",
            arguments=_DeleteArgs(entity_id=str(uuid4()), confirm=False),
        )
        state = AgentState(
            thread_id=f"{acc_id}:{uuid4()}",
            account_id=_UUID(acc_id),
            user_id=_UUID(usr_id),
            user_message="del",
            context_json=ContextJson(page_route="/chat"),
            agent_run_id=_UUID(run_id),
        )
        result = await dispatch(call, state, db)
        # Pending confirmation (pas exécuté)
        assert result.kind == "frontend_event"
        assert result.status == "pending_confirmation"
        assert invocations["count"] == 0

        # Vérifie que pending stocké dans agent_run.metadata
        meta = db.execute(
            text("SELECT metadata FROM agent_run WHERE id = :r"),
            {"r": run_id},
        ).scalar_one()
        if isinstance(meta, str):
            meta = json.loads(meta)
        assert "pending_confirmations" in meta
        assert call.id in meta["pending_confirmations"]


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
@pytest.mark.asyncio
async def test_user_says_no_cancels_via_consume(db_engine):
    """Stocke pending puis consume avec response='no' → cancelled_by_user."""
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    _setup_delete_tool()
    with Session() as db:
        acc_id, usr_id, run_id = _bootstrap_account_and_run(db)
        from uuid import UUID as _UUID

        from app.agent.confirmation import (
            build_pending_confirmation,
            consume_confirmation,
            store_pending_confirmation,
        )

        unique_id = f"cdel_no_{uuid4().hex}"
        pending = build_pending_confirmation(
            tool_call_id=unique_id,
            tool_name="delete_test_thing",
            arguments={"entity_id": "x"},
            ttl_seconds=300,
        )
        store_pending_confirmation(
            db, agent_run_id=_UUID(run_id), pending=pending
        )
        db.commit()

        consumed, status = consume_confirmation(
            db,
            agent_run_id=_UUID(run_id),
            call_id=unique_id,
            user_response="no",
        )
        assert status == "cancelled_by_user"
        assert consumed is None


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
@pytest.mark.asyncio
async def test_user_says_yes_executes(db_engine):
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    invocations = _setup_delete_tool()
    with Session() as db:
        acc_id, usr_id, run_id = _bootstrap_account_and_run(db)
        from uuid import UUID as _UUID

        # Étape 1 : déclencher pending avec confirm absent
        # Pour vraiment tester yes, on stocke nous-mêmes un pending puis on
        # dispatch avec confirm=True.
        from app.agent.confirmation import (
            build_pending_confirmation,
            store_pending_confirmation,
        )

        unique_yes = f"cdel_yes_{uuid4().hex}"
        pending = build_pending_confirmation(
            tool_call_id=unique_yes,
            tool_name="delete_test_thing",
            arguments={"entity_id": "x"},
            ttl_seconds=300,
        )
        store_pending_confirmation(
            db, agent_run_id=_UUID(run_id), pending=pending
        )
        db.commit()

        # Maintenant dispatch avec confirm=True
        call_yes = ValidatedToolCall(
            id=unique_yes,
            name="delete_test_thing",
            arguments=_DeleteArgs(entity_id="x", confirm=True),
        )
        state = AgentState(
            thread_id=f"{acc_id}:{uuid4()}",
            account_id=_UUID(acc_id),
            user_id=_UUID(usr_id),
            user_message="del",
            context_json=ContextJson(page_route="/chat"),
            agent_run_id=_UUID(run_id),
        )
        result = await dispatch(call_yes, state, db)
        assert result.kind == "mutation_result"
        assert invocations["count"] == 1
