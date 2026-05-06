"""F55 / T101 — Integration test idempotency replay.

Vérifie qu'un même `(account_id, agent_run_id, call_id)` ne re-crée jamais
la mutation et retourne le même ToolDispatchResult.
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from app.agent.dispatcher import dispatch
from app.agent.mutation_handlers import (
    mutation_handler,
    reset_mutation_handlers,
)
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


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")
    v: int = 1


@pytest.fixture(autouse=True)
def _isolation():
    backup = dict(TOOL_REGISTRY)
    reset_registry()
    reset_mutation_handlers()
    yield
    reset_registry()
    reset_mutation_handlers()
    TOOL_REGISTRY.update(backup)


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
@pytest.mark.asyncio
async def test_replay_returns_existing_no_duplicate(db_engine):
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    tool(
        name="create_idem_test",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_Args,
        category=ToolCategory.MUTATION,
    )

    invocations = {"count": 0}

    @mutation_handler("create_idem_test")
    async def _h(args, ctx):
        invocations["count"] += 1
        return MutationResult(
            entity_type="x",
            entity_id=uuid4(),
            fields_updated=["v"],
            snapshot={"v": args.v},
        )

    with Session() as db:
        acc_id = db.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'IdemTest', now(), now()) RETURNING id"
            )
        ).scalar_one()
        usr_id = db.execute(
            text(
                "INSERT INTO account_user (id, account_id, email, password_hash, "
                "role, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :a, :e, 'h', 'pme', now(), now()) RETURNING id"
            ),
            {"a": acc_id, "e": f"idem_{uuid4()}@x.com"},
        ).scalar_one()
        db.commit()

        db.execute(text(f"SET LOCAL \"app.current_account_id\" = '{acc_id}'"))
        db.execute(text(f"SET LOCAL \"app.current_user_id\" = '{usr_id}'"))

        unique_call_id = f"cidem_{uuid4().hex}"
        call = ValidatedToolCall(
            id=unique_call_id, name="create_idem_test", arguments=_Args(v=42)
        )
        state = AgentState(
            thread_id=f"{acc_id}:{uuid4()}",
            account_id=acc_id,
            user_id=usr_id,
            user_message="hi",
            context_json=ContextJson(page_route="/chat"),
            agent_run_id=None,  # même valeur dans les 2 dispatches
        )

        # 1ère exécution
        result1 = await dispatch(call, state, db)
        assert result1.kind == "mutation_result"
        assert invocations["count"] == 1

        # 2e exécution avec même call_id → idempotency hit
        result2 = await dispatch(call, state, db)
        # Le handler ne doit PAS être ré-exécuté
        assert invocations["count"] == 1
        # Le résultat reconstruit doit être le même tool_call_id
        assert result2.tool_call_id == result1.tool_call_id


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
@pytest.mark.asyncio
async def test_distinct_accounts_no_idempotency_collision(db_engine):
    """Deux accounts différents avec même call_id ne se collisionnent pas."""
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    tool(
        name="create_idem_distinct",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_Args,
        category=ToolCategory.MUTATION,
    )

    invocations = {"count": 0}

    @mutation_handler("create_idem_distinct")
    async def _h(args, ctx):
        invocations["count"] += 1
        return MutationResult(
            entity_type="x",
            entity_id=uuid4(),
            fields_updated=["v"],
        )

    with Session() as db:
        # Crée deux accounts
        acc_a = db.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'A', now(), now()) RETURNING id"
            )
        ).scalar_one()
        acc_b = db.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'B', now(), now()) RETURNING id"
            )
        ).scalar_one()
        usr_a = db.execute(
            text(
                "INSERT INTO account_user (id, account_id, email, password_hash, "
                "role, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :a, :e, 'h', 'pme', now(), now()) RETURNING id"
            ),
            {"a": acc_a, "e": f"a_{uuid4()}@x.com"},
        ).scalar_one()
        usr_b = db.execute(
            text(
                "INSERT INTO account_user (id, account_id, email, password_hash, "
                "role, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :a, :e, 'h', 'pme', now(), now()) RETURNING id"
            ),
            {"a": acc_b, "e": f"b_{uuid4()}@x.com"},
        ).scalar_one()
        db.commit()

        # Compte A
        db.execute(text(f"SET LOCAL \"app.current_account_id\" = '{acc_a}'"))
        db.execute(text(f"SET LOCAL \"app.current_user_id\" = '{usr_a}'"))
        same_call_id = f"cdistinct_{uuid4().hex}"
        call_a = ValidatedToolCall(
            id=same_call_id,
            name="create_idem_distinct",
            arguments=_Args(v=1),
        )
        state_a = AgentState(
            thread_id=f"{acc_a}:{uuid4()}",
            account_id=acc_a,
            user_id=usr_a,
            user_message="hi",
            context_json=ContextJson(page_route="/chat"),
        )
        r_a = await dispatch(call_a, state_a, db)

        # Compte B avec même call_id
        db.execute(text(f"SET LOCAL \"app.current_account_id\" = '{acc_b}'"))
        db.execute(text(f"SET LOCAL \"app.current_user_id\" = '{usr_b}'"))
        call_b = ValidatedToolCall(
            id=same_call_id,
            name="create_idem_distinct",
            arguments=_Args(v=1),
        )
        state_b = AgentState(
            thread_id=f"{acc_b}:{uuid4()}",
            account_id=acc_b,
            user_id=usr_b,
            user_message="hi",
            context_json=ContextJson(page_route="/chat"),
        )
        r_b = await dispatch(call_b, state_b, db)

        # Deux invocations distinctes : pas de collision
        assert invocations["count"] == 2
        assert r_a.kind == "mutation_result"
        assert r_b.kind == "mutation_result"
