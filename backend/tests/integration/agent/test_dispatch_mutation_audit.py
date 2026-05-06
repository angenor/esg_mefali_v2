"""F55 / T031 — Integration test mutation + audit + tool_call_log.

Crée un compte minimal, déclare un handler de mutation custom, dispatch le
tool, vérifie :
1. tool_call_log ligne créée avec status='ok' + dispatch_result_kind='mutation_result'
2. audit_log ligne créée avec source_of_change='llm' + tool_call_id renseigné
3. handler exception → ROLLBACK transactionnel (pas de ligne audit, pas de
   ligne business).
"""

from __future__ import annotations

from uuid import uuid4

import pytest
from pydantic import BaseModel, ConfigDict
from sqlalchemy import text

from app.agent.dispatcher import dispatch
from app.agent.mutation_ctx import MutationCtx
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


class _UpdateArgs(BaseModel):
    model_config = ConfigDict(extra="forbid")
    payload: str = "x"


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
async def test_mutation_creates_tool_call_log_and_audit(db_engine):
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)

    # Setup : tool + handler
    tool(
        name="update_test_audit",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_UpdateArgs,
        category=ToolCategory.MUTATION,
    )

    captured: dict = {}

    @mutation_handler("update_test_audit")
    async def _handler(args: _UpdateArgs, ctx: MutationCtx) -> MutationResult:
        # Émet une ligne audit via le ctx.audit_logger
        eid = uuid4()
        audit_id = ctx.audit_logger(
            entity_type="entreprise_test_audit",
            entity_id=eid,
            field="payload",
            old=None,
            new={"value": args.payload},
            source_of_change="llm",
        )
        captured["entity_id"] = eid
        captured["audit_id"] = audit_id
        return MutationResult(
            entity_type="entreprise_test_audit",
            entity_id=eid,
            fields_updated=["payload"],
            audit_log_id=audit_id,
            snapshot={"payload": args.payload},
        )

    with Session() as db:
        # Bootstrap account row
        acc_id = db.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'F55Test', now(), now()) RETURNING id"
            )
        ).scalar_one()
        usr_id = db.execute(
            text(
                "INSERT INTO account_user (id, account_id, email, password_hash, "
                "role, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :a, :e, 'h', 'pme', now(), now()) RETURNING id"
            ),
            {"a": acc_id, "e": f"f55_{uuid4()}@x.com"},
        ).scalar_one()
        db.commit()

        # Active RLS
        db.execute(text(f"SET LOCAL \"app.current_account_id\" = '{acc_id}'"))
        db.execute(text(f"SET LOCAL \"app.current_user_id\" = '{usr_id}'"))

        unique_call_id = f"cint_{uuid4().hex}"
        call = ValidatedToolCall(
            id=unique_call_id,
            name="update_test_audit",
            arguments=_UpdateArgs(payload="hello"),
        )
        state = AgentState(
            thread_id=f"{acc_id}:{uuid4()}",
            account_id=acc_id,
            user_id=usr_id,
            user_message="hi",
            context_json=ContextJson(page_route="/chat"),
        )
        result = await dispatch(call, state, db)

        assert result.kind == "mutation_result", f"unexpected: {result}"
        assert result.status == "ok"
        assert result.entity_type == "entreprise_test_audit"

        # Vérifie tool_call_log
        log_rows = db.execute(
            text(
                "SELECT status, dispatch_result_kind, idempotency_key, agent_run_id "
                "FROM tool_call_log WHERE tool_call_id = :tc"
            ),
            {"tc": unique_call_id},
        ).mappings().all()
        assert len(log_rows) == 1
        assert log_rows[0]["status"] == "ok"
        assert log_rows[0]["dispatch_result_kind"] == "mutation_result"
        assert log_rows[0]["idempotency_key"] is not None

        # Vérifie audit_log
        audit_rows = db.execute(
            text(
                "SELECT source_of_change, tool_call_id, agent_run_id, field "
                "FROM audit_log WHERE entity_id = :eid"
            ),
            {"eid": str(captured["entity_id"])},
        ).mappings().all()
        assert len(audit_rows) >= 1
        ar = audit_rows[0]
        assert str(ar["source_of_change"]) == "llm"
        assert ar["tool_call_id"] is not None  # FK F55
        assert ar["field"] == "payload"


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
@pytest.mark.asyncio
async def test_handler_exception_rolls_back(db_engine):
    from sqlalchemy.orm import sessionmaker

    Session = sessionmaker(bind=db_engine)
    tool(
        name="update_test_fails",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_UpdateArgs,
        category=ToolCategory.MUTATION,
    )

    @mutation_handler("update_test_fails")
    async def _bad(args, ctx):
        # Insère puis raise → rollback attendu
        ctx.audit_logger(
            entity_type="x",
            entity_id=uuid4(),
            field="f",
            old=None,
            new={"v": "before_crash"},
            source_of_change="llm",
        )
        raise RuntimeError("forced_failure")

    with Session() as db:
        acc_id = db.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'F55Fail', now(), now()) RETURNING id"
            )
        ).scalar_one()
        usr_id = db.execute(
            text(
                "INSERT INTO account_user (id, account_id, email, password_hash, "
                "role, created_at, updated_at) "
                "VALUES (gen_random_uuid(), :a, :e, 'h', 'pme', now(), now()) RETURNING id"
            ),
            {"a": acc_id, "e": f"f55_{uuid4()}@x.com"},
        ).scalar_one()
        db.commit()

        db.execute(text(f"SET LOCAL \"app.current_account_id\" = '{acc_id}'"))
        db.execute(text(f"SET LOCAL \"app.current_user_id\" = '{usr_id}'"))

        call = ValidatedToolCall(
            id=f"cfail_{uuid4().hex}",
            name="update_test_fails",
            arguments=_UpdateArgs(payload="boom"),
        )
        state = AgentState(
            thread_id=f"{acc_id}:{uuid4()}",
            account_id=acc_id,
            user_id=usr_id,
            user_message="hi",
            context_json=ContextJson(page_route="/chat"),
        )
        # Ne raise pas — l'exception est rattrapée et retournée comme error
        result = await dispatch(call, state, db)
        assert result.kind == "error"
        assert "forced_failure" in (result.error_summary or "")

        # Le rollback doit avoir effacé la ligne audit insérée par le handler
        bad_audit = db.execute(
            text(
                "SELECT COUNT(*) FROM audit_log "
                "WHERE new_value::text LIKE '%before_crash%'"
            )
        ).scalar_one()
        assert bad_audit == 0
