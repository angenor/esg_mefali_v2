"""F56 / T021 — Tests integration de ``handle_flag_unsourced``.

Couvre :
- Insert OK + ligne créée + audit + SSE.
- ON CONFLICT DO NOTHING (dédup intra-thread, FR-006).
- RLS account_id strict (cross-tenant invisible).
- Validation Pydantic (longueur claim/reason).
"""

from __future__ import annotations

import time
import uuid
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy import text

from app.agent.handlers.flag_unsourced import handle_flag_unsourced
from app.agent.mutation_ctx import MutationCtx
from app.agent.sourcing.tool_schemas import FlagUnsourcedArgs
from app.db import SessionLocal
from app.scripts.seed_admin import create_admin
from tests.conftest import requires_db


@pytest.fixture()
def acc_user_ids():
    db = SessionLocal()
    try:
        u = create_admin(
            db,
            email=f"f56_u_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@x.com",
            password="Sup3rSecret!Pass",
        )
        acc_id = db.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'F56 flag test', now(), now()) "
                "RETURNING id"
            )
        ).scalar_one()
        db.commit()
        return acc_id, u.id
    finally:
        db.close()


@pytest.fixture()
def db_session(acc_user_ids):
    acc_id, _ = acc_user_ids
    db = SessionLocal()
    db.execute(text(f"SET LOCAL \"app.current_account_id\" = '{acc_id}'"))
    yield db
    try:
        db.rollback()
    except Exception:
        pass
    db.close()


def _make_ctx(db, account_id, user_id) -> MutationCtx:
    audit_logger = MagicMock(return_value=uuid.uuid4())
    publisher = AsyncMock()
    return MutationCtx(
        account_id=account_id,
        user_id=user_id,
        db=db,
        audit_logger=audit_logger,
        event_bus_publisher=publisher,
        tool_call_log_id=uuid.uuid4(),
        agent_run_id=None,
        dry_run=False,
    )


@requires_db
@pytest.mark.integration
async def test_flag_unsourced_inserts_and_returns_id(acc_user_ids, db_session):
    acc_id, u_id = acc_user_ids
    ctx = _make_ctx(db_session, acc_id, u_id)
    args = FlagUnsourcedArgs(
        claim="Le BOAD acceptera le dossier en 8 semaines",
        reason="aucune source publique",
    )
    result = await handle_flag_unsourced(args, ctx)
    assert result.entity_type == "unsourced_flag"
    assert result.snapshot == {
        "claim": args.claim,
        "reason": args.reason,
    }
    # Audit logger appelé
    ctx.audit_logger.assert_called_once()
    # SSE publisher appelé
    ctx.event_bus_publisher.assert_awaited_once()
    sse_args = ctx.event_bus_publisher.await_args
    assert sse_args.args[1] == "unsourced_claim"


@requires_db
@pytest.mark.integration
async def test_flag_unsourced_dedup_on_conflict(acc_user_ids, db_session):
    """Deux insertions identiques (même thread NULL ; même claim) → 1 seule ligne."""
    acc_id, u_id = acc_user_ids
    ctx = _make_ctx(db_session, acc_id, u_id)
    args = FlagUnsourcedArgs(
        claim="même affirmation à dédup",
        reason="raison 1",
    )
    await handle_flag_unsourced(args, ctx)

    # Deuxième invocation — silently ignored par ON CONFLICT
    args2 = FlagUnsourcedArgs(
        claim="même affirmation à dédup",
        reason="raison 2",
    )
    result2 = await handle_flag_unsourced(args2, ctx)
    # Le second appel n'a pas levé d'erreur ; il a renvoyé un MutationResult
    # mais le dispatcher le traduira en "skipped" si fields_updated est vide.
    assert result2.entity_type == "unsourced_flag"

    # Vérification SQL : exactement 1 ligne pour ce claim
    count = db_session.execute(
        text(
            "SELECT count(*) FROM unsourced_flag "
            "WHERE account_id = :a AND lower(claim) = :c"
        ),
        {"a": str(acc_id), "c": "même affirmation à dédup"},
    ).scalar()
    assert count == 1


@requires_db
@pytest.mark.integration
async def test_flag_unsourced_rls_isolates_tenants(acc_user_ids, db_session):
    """Account A insère ; Account B (avec son propre RLS) ne voit pas la ligne."""
    acc_a, u_id = acc_user_ids
    ctx = _make_ctx(db_session, acc_a, u_id)
    await handle_flag_unsourced(
        FlagUnsourcedArgs(claim="rls test claim", reason="r"), ctx
    )

    # Compte avec set RLS = autre account
    other_db = SessionLocal()
    try:
        # Créer un autre account
        other_acc = other_db.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'other', now(), now()) RETURNING id"
            )
        ).scalar_one()
        other_db.execute(
            text(f"SET LOCAL \"app.current_account_id\" = '{other_acc}'")
        )
        rows = other_db.execute(
            text("SELECT id FROM unsourced_flag WHERE lower(claim) = 'rls test claim'")
        ).all()
        # Sous RLS de other_acc, la ligne de acc_a est invisible
        assert rows == []
    finally:
        try:
            other_db.rollback()
        except Exception:
            pass
        other_db.close()


@pytest.mark.unit
def test_flag_unsourced_args_pydantic_validation():
    """Validation des bornes (sans DB)."""
    from pydantic import ValidationError

    # claim trop long
    with pytest.raises(ValidationError):
        FlagUnsourcedArgs(claim="x" * 1100, reason="r")
    # reason trop long
    with pytest.raises(ValidationError):
        FlagUnsourcedArgs(claim="c", reason="x" * 600)
    # claim vide
    with pytest.raises(ValidationError):
        FlagUnsourcedArgs(claim="", reason="r")


@pytest.mark.unit
def test_flag_unsourced_extra_field_rejected():
    from pydantic import ValidationError

    with pytest.raises(ValidationError):
        FlagUnsourcedArgs(claim="c", reason="r", extra="bad")  # type: ignore[call-arg]
