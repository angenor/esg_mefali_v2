"""F56 / T014 — Tests integration de ``cite_source_handler`` (FR-003).

Couvre :
- Source verified → success.
- UUID inconnu → ``error: source_not_found``.
- Source pending → ``error: source_unverified``.
- Source outdated → ``error: source_unverified`` (Q3).
"""

from __future__ import annotations

import time
import uuid
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.agent.handlers.cite_source import cite_source_handler
from app.agent.sourcing.tool_schemas import CiteSourceArgs
from app.agent.state import AgentState, ContextJson, ValidatedToolCall
from app.db import SessionLocal, get_engine_migrator
from app.scripts.seed_admin import create_admin
from app.services import source_service
from tests.conftest import requires_db


def _build_state(account_id: uuid.UUID) -> AgentState:
    return AgentState(
        thread_id=f"{account_id}:{uuid4()}",
        account_id=account_id,
        user_id=uuid4(),
        user_message="hello",
        context_json=ContextJson(page_route="/chat"),
    )


def _stub_emb(_):
    return [[0.0] * 1024]


@pytest.fixture()
def admin_account_ids():
    db = SessionLocal()
    try:
        a = create_admin(
            db,
            email=f"f56_a_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com",
            password="Sup3rSecret!Pass",
        )
        b = create_admin(
            db,
            email=f"f56_b_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com",
            password="Sup3rSecret!Pass",
        )
        # Create a tenant account for state.account_id (admins have NULL account_id)
        acc_id = db.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'F56 test', now(), now()) "
                "RETURNING id"
            )
        ).scalar_one()
        db.commit()
        return a.id, b.id, acc_id
    finally:
        db.close()


@pytest.fixture()
def verified_source(admin_account_ids):
    a_id, b_id, _ = admin_account_ids
    eng = get_engine_migrator()
    with eng.begin() as c:
        sid = source_service.create_pending(
            c,
            captured_by=a_id,
            url=f"https://example.com/{uuid.uuid4()}",
            title="ADEME Base Carbone v23",
            publisher="ADEME",
        )
        source_service.verify(
            c, source_id=sid, verifier_id=b_id, embedding_func=_stub_emb
        )
    return sid


@pytest.fixture()
def pending_source(admin_account_ids):
    a_id, _, _ = admin_account_ids
    eng = get_engine_migrator()
    with eng.begin() as c:
        sid = source_service.create_pending(
            c,
            captured_by=a_id,
            url=f"https://example.com/pending/{uuid.uuid4()}",
            title="Pending source",
            publisher="GCF",
        )
    return sid


@pytest.fixture()
def outdated_source(admin_account_ids):
    a_id, b_id, _ = admin_account_ids
    eng = get_engine_migrator()
    with eng.begin() as c:
        sid = source_service.create_pending(
            c,
            captured_by=a_id,
            url=f"https://example.com/outdated/{uuid.uuid4()}",
            title="Outdated source",
            publisher="Other",
        )
        source_service.verify(
            c, source_id=sid, verifier_id=b_id, embedding_func=_stub_emb
        )
        c.execute(
            text(
                "UPDATE source SET verification_status = 'outdated' "
                "WHERE id = :sid"
            ),
            {"sid": str(sid)},
        )
    return sid


@requires_db
@pytest.mark.integration
async def test_cite_source_returns_metadata_for_verified(
    admin_account_ids, verified_source
):
    _, _, account_id = admin_account_ids
    state = _build_state(account_id)
    call = ValidatedToolCall(
        id="t1",
        name="cite_source",
        arguments=CiteSourceArgs(source_id=verified_source),
    )
    result = await cite_source_handler(state, call)
    assert result.get("error") is None, result
    assert result["source_id"] == str(verified_source)
    assert result["verification_status"] == "verified"
    assert result["title"] == "ADEME Base Carbone v23"
    assert result["publisher"] == "ADEME"


@requires_db
@pytest.mark.integration
async def test_cite_source_returns_not_found_for_unknown_uuid(admin_account_ids):
    _, _, account_id = admin_account_ids
    state = _build_state(account_id)
    call = ValidatedToolCall(
        id="t2",
        name="cite_source",
        arguments=CiteSourceArgs(source_id=uuid4()),
    )
    result = await cite_source_handler(state, call)
    assert result["error"] == "source_not_found"
    assert "search_source" in result.get("hint", "")


@requires_db
@pytest.mark.integration
async def test_cite_source_returns_unverified_for_pending(
    admin_account_ids, pending_source
):
    _, _, account_id = admin_account_ids
    state = _build_state(account_id)
    call = ValidatedToolCall(
        id="t3",
        name="cite_source",
        arguments=CiteSourceArgs(source_id=pending_source),
    )
    result = await cite_source_handler(state, call)
    assert result["error"] == "source_unverified"
    assert result["current_status"] == "pending"


@requires_db
@pytest.mark.integration
async def test_cite_source_rejects_outdated_strict(
    admin_account_ids, outdated_source
):
    """Q3 — outdated est aussi rejeté strictement."""
    _, _, account_id = admin_account_ids
    state = _build_state(account_id)
    call = ValidatedToolCall(
        id="t4",
        name="cite_source",
        arguments=CiteSourceArgs(source_id=outdated_source),
    )
    result = await cite_source_handler(state, call)
    assert result["error"] == "source_unverified"
    assert result["current_status"] == "outdated"
