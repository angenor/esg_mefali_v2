"""F55 / T100 — Integration test rate limit 31/60s.

Vérifie : 30 succès puis 31e refusée avec status='rate_limited'.
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
from app.agent.rate_limit import (
    InMemoryRateLimitStore,
    set_rate_store,
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
    v: int = 0


@pytest.fixture(autouse=True)
def _isolation():
    backup = dict(TOOL_REGISTRY)
    reset_registry()
    reset_mutation_handlers()
    # Fresh in-memory store per test
    set_rate_store(InMemoryRateLimitStore())
    yield
    reset_registry()
    reset_mutation_handlers()
    set_rate_store(None)
    TOOL_REGISTRY.update(backup)


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
@pytest.mark.asyncio
async def test_31_calls_30_ok_1_rate_limited(db_engine):
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    tool(
        name="update_rate_test",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_Args,
        category=ToolCategory.MUTATION,
    )

    @mutation_handler("update_rate_test")
    async def _h(args, ctx):
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
                "VALUES (gen_random_uuid(), 'RT', now(), now()) RETURNING id"
            )
        ).scalar_one()
        usr_id = db.execute(
            text(
                "INSERT INTO account_user (id, account_id, email, password_hash, "
                "role, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :a, :e, 'h', 'pme', now(), now()) RETURNING id"
            ),
            {"a": acc_id, "e": f"rt_{uuid4()}@x.com"},
        ).scalar_one()
        db.commit()

        db.execute(text(f"SET LOCAL \"app.current_account_id\" = '{acc_id}'"))
        db.execute(text(f"SET LOCAL \"app.current_user_id\" = '{usr_id}'"))

        ok_count = 0
        rate_limited_count = 0
        prefix = f"crl_{uuid4().hex}"
        for i in range(31):
            call = ValidatedToolCall(
                id=f"{prefix}_{i}",
                name="update_rate_test",
                arguments=_Args(v=i),
            )
            state = AgentState(
                thread_id=f"{acc_id}:{uuid4()}",
                account_id=acc_id,
                user_id=usr_id,
                user_message="hi",
                context_json=ContextJson(page_route="/chat"),
            )
            result = await dispatch(call, state, db)
            if result.status == "ok":
                ok_count += 1
            elif result.status == "rate_limited":
                rate_limited_count += 1

        assert ok_count == 30
        assert rate_limited_count == 1


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
@pytest.mark.asyncio
async def test_rate_limit_store_unavailable_fail_safe(db_engine):
    """NFR-007 : si le store est down, mutations refusées (fail-safe)."""
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    tool(
        name="update_safe_test",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_Args,
        category=ToolCategory.MUTATION,
    )

    @mutation_handler("update_safe_test")
    async def _h(args, ctx):
        return MutationResult(
            entity_type="x", entity_id=uuid4(), fields_updated=["v"]
        )

    # Force store down
    bad_store = InMemoryRateLimitStore()
    bad_store._set_healthy(False)
    set_rate_store(bad_store)

    with Session() as db:
        acc_id = db.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'FailSafe', now(), now()) RETURNING id"
            )
        ).scalar_one()
        usr_id = db.execute(
            text(
                "INSERT INTO account_user (id, account_id, email, password_hash, "
                "role, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :a, :e, 'h', 'pme', now(), now()) RETURNING id"
            ),
            {"a": acc_id, "e": f"fs_{uuid4()}@x.com"},
        ).scalar_one()
        db.commit()

        db.execute(text(f"SET LOCAL \"app.current_account_id\" = '{acc_id}'"))
        db.execute(text(f"SET LOCAL \"app.current_user_id\" = '{usr_id}'"))

        call = ValidatedToolCall(
            id=f"cfs_{uuid4().hex}", name="update_safe_test", arguments=_Args(v=1)
        )
        state = AgentState(
            thread_id=f"{acc_id}:{uuid4()}",
            account_id=acc_id,
            user_id=usr_id,
            user_message="hi",
            context_json=ContextJson(page_route="/chat"),
        )
        result = await dispatch(call, state, db)
        assert result.kind == "error"
        assert result.error_summary == "rate_limit_unavailable"
