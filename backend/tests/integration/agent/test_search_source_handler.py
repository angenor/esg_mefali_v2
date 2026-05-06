"""F56 / T017 — Tests integration de ``search_source_handler``.

Couvre :
- Voyage OK → cosine top-N (mocké pour stabilité).
- Voyage error → fallback ILIKE avec ``degraded=True``.
- 0 result → ``hint='no_match — consider flag_unsourced'``.
"""

from __future__ import annotations

import time
import uuid
from unittest.mock import patch
from uuid import uuid4

import pytest
from sqlalchemy import text

from app.agent.handlers.search_source import search_source_handler
from app.agent.sourcing.tool_schemas import SearchSourceArgs
from app.agent.state import AgentState, ContextJson, ValidatedToolCall
from app.db import SessionLocal, get_engine_migrator
from app.scripts.seed_admin import create_admin
from app.services import source_service
from tests.conftest import requires_db


def _stub_emb(_):
    # 1024-dim (matche la colonne pgvector)
    return [[0.1] * 1024]


@pytest.fixture()
def admin_account_ids():
    db = SessionLocal()
    try:
        a = create_admin(
            db,
            email=f"f56s_a_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@x.com",
            password="Sup3rSecret!Pass",
        )
        b = create_admin(
            db,
            email=f"f56s_b_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@x.com",
            password="Sup3rSecret!Pass",
        )
        acc_id = db.execute(
            text(
                "INSERT INTO account (id, name, created_at, updated_at) "
                "VALUES (gen_random_uuid(), 'F56 search', now(), now()) "
                "RETURNING id"
            )
        ).scalar_one()
        db.commit()
        return a.id, b.id, acc_id
    finally:
        db.close()


@pytest.fixture()
def seeded_sources(admin_account_ids):
    a_id, b_id, _ = admin_account_ids
    eng = get_engine_migrator()
    sids: list[uuid.UUID] = []
    with eng.begin() as c:
        for title in [
            "ADEME Base Carbone v23 — Diesel",
            "GCF SME Threshold 2024",
            "BOAD Annual Report 2023",
        ]:
            sid = source_service.create_pending(
                c,
                captured_by=a_id,
                url=f"https://example.com/{uuid.uuid4()}",
                title=title,
                publisher=title.split()[0],
            )
            source_service.verify(
                c, source_id=sid, verifier_id=b_id, embedding_func=_stub_emb
            )
            sids.append(sid)
    return sids


def _state(account_id) -> AgentState:
    return AgentState(
        thread_id=f"{account_id}:{uuid4()}",
        account_id=account_id,
        user_id=uuid4(),
        user_message="hello",
        context_json=ContextJson(page_route="/chat"),
    )


@requires_db
@pytest.mark.integration
async def test_search_source_voyage_ok_returns_results(
    admin_account_ids, seeded_sources
):
    _, _, acc_id = admin_account_ids
    state = _state(acc_id)
    call = ValidatedToolCall(
        id="t1",
        name="search_source",
        arguments=SearchSourceArgs(query="diesel ADEME", limit=3),
    )
    # Mock voyage embedding
    with patch(
        "app.embeddings_client.embed",
        return_value=[[0.1] * 1024],
    ):
        result = await search_source_handler(state, call)
    assert result["degraded"] is False
    assert len(result["results"]) >= 1
    # Tous filtered = verified
    for r in result["results"]:
        assert "id" in r and "title" in r


@requires_db
@pytest.mark.integration
async def test_search_source_voyage_error_falls_back_to_ilike(
    admin_account_ids, seeded_sources
):
    _, _, acc_id = admin_account_ids
    state = _state(acc_id)
    call = ValidatedToolCall(
        id="t2",
        name="search_source",
        arguments=SearchSourceArgs(query="ADEME", limit=3),
    )
    from app.embeddings_client import VoyageError

    with patch(
        "app.embeddings_client.embed",
        side_effect=VoyageError("voyage_down"),
    ):
        result = await search_source_handler(state, call)
    assert result["degraded"] is True
    # Au moins ADEME doit ressortir avec ILIKE
    assert any("ADEME" in (r["title"] or "") for r in result["results"])


@requires_db
@pytest.mark.integration
async def test_search_source_no_match_hint(admin_account_ids, seeded_sources):
    _, _, acc_id = admin_account_ids
    state = _state(acc_id)
    call = ValidatedToolCall(
        id="t3",
        name="search_source",
        arguments=SearchSourceArgs(
            query="xyzqzqz_unlikely_term_no_match", limit=3
        ),
    )
    from app.embeddings_client import VoyageError

    with patch(
        "app.embeddings_client.embed",
        side_effect=VoyageError("voyage_down"),
    ):
        result = await search_source_handler(state, call)
    assert result["results"] == []
    assert "no_match" in result.get("hint", "")
