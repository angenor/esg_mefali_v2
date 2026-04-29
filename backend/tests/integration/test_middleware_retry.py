"""F03 US3 — Tests integration middleware anti-hallucination."""

from __future__ import annotations

import time
import uuid

import pytest

from app.db import SessionLocal, get_engine_migrator
from app.scripts.seed_admin import create_admin
from app.services import source_service
from app.services.llm_validation import (
    ESCAPE_HATCH_MESSAGE,
    apply_to_llm_response,
    decision_cache,
    validate_llm_output,
)
from tests.integration.conftest import requires_db


def _stub_emb(_):
    return [[0.0] * 1024]


@pytest.fixture()
def verified_sid():
    db = SessionLocal()
    try:
        a = create_admin(
            db,
            email=f"m_a_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com",
            password="Sup3rSecret!Pass",
        )
        b = create_admin(
            db,
            email=f"m_b_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com",
            password="Sup3rSecret!Pass",
        )
        db.commit()
        a_id = a.id
        b_id = b.id
    finally:
        db.close()
    eng = get_engine_migrator()
    with eng.begin() as c:
        sid = source_service.create_pending(
            c,
            captured_by=a_id,
            url="https://x.example/m",
            title="MID Test",
            publisher="GCF",
        )
        source_service.verify(
            c, source_id=sid, verifier_id=b_id, embedding_func=_stub_emb
        )
    return sid


@pytest.fixture()
def pending_sid():
    db = SessionLocal()
    try:
        a = create_admin(
            db,
            email=f"mp_a_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com",
            password="Sup3rSecret!Pass",
        )
        db.commit()
        a_id = a.id
    finally:
        db.close()
    eng = get_engine_migrator()
    with eng.begin() as c:
        sid = source_service.create_pending(
            c,
            captured_by=a_id,
            url="https://x.example/mp",
            title="MIDP Test",
            publisher="GCF",
        )
    return sid


@pytest.fixture(autouse=True)
def _clear_cache():
    decision_cache.clear()
    yield
    decision_cache.clear()


@requires_db
class TestMiddleware:
    def test_rejects_esg_claim_without_citation(self):
        db = SessionLocal()
        try:
            d = validate_llm_output(
                db,
                {
                    "role": "assistant",
                    "content": "Le seuil GCF est 30%.",
                    "tool_calls": [],
                },
            )
            assert d.accepted is False
            assert d.reason_code == "heuristic_match_no_tool"
        finally:
            db.close()

    def test_accepts_with_verified_cite(self, verified_sid):
        db = SessionLocal()
        try:
            d = validate_llm_output(
                db,
                {
                    "role": "assistant",
                    "content": "Le seuil GCF est 30%.",
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {
                                "name": "cite_source",
                                "arguments": f'{{"source_id": "{verified_sid}"}}',
                            },
                        }
                    ],
                },
            )
            assert d.accepted is True
            assert d.reason_code == "ok"
        finally:
            db.close()

    def test_rejects_when_cite_pending(self, pending_sid):
        db = SessionLocal()
        try:
            d = validate_llm_output(
                db,
                {
                    "role": "assistant",
                    "content": "Le seuil GCF est 30%.",
                    "tool_calls": [
                        {
                            "id": "c1",
                            "type": "function",
                            "function": {
                                "name": "cite_source",
                                "arguments": f'{{"source_id": "{pending_sid}"}}',
                            },
                        }
                    ],
                },
            )
            assert d.accepted is False
            assert d.reason_code == "source_not_verified"
        finally:
            db.close()

    def test_escape_hatch_after_2_retries(self):
        db = SessionLocal()
        try:
            initial = {
                "role": "assistant",
                "content": "Le ticket est 5 000 000 FCFA.",
                "tool_calls": [],
            }
            attempts = {"i": 0}

            def llm_call():
                attempts["i"] += 1
                # toujours sans citation
                return {
                    "role": "assistant",
                    "content": "Toujours 5 000 000 FCFA.",
                    "tool_calls": [],
                }

            msg, decision = apply_to_llm_response(
                db,
                llm_call=llm_call,
                initial_message=initial,
                max_retries=2,
            )
            assert decision.accepted is False
            assert msg["content"] == ESCAPE_HATCH_MESSAGE
            assert attempts["i"] == 2
        finally:
            db.close()

    def test_cache_hit_second_call(self, verified_sid):
        db = SessionLocal()
        try:
            msg = {
                "role": "assistant",
                "content": "Le seuil GCF est 30%.",
                "tool_calls": [
                    {
                        "id": "c1",
                        "type": "function",
                        "function": {
                            "name": "cite_source",
                            "arguments": f'{{"source_id": "{verified_sid}"}}',
                        },
                    }
                ],
            }
            d1 = validate_llm_output(db, msg)
            assert d1.accepted is True
            sz1 = decision_cache.size()
            d2 = validate_llm_output(db, msg)
            assert d2.accepted is True
            # cache déjà populé
            assert decision_cache.size() == sz1
        finally:
            db.close()
