"""F03 US2 — Tests integration routes /internal/llm-tools/*."""

from __future__ import annotations

import time
import uuid

import pytest

from app.db import SessionLocal, get_engine_migrator
from app.scripts.seed_admin import create_admin
from app.services import source_service
from tests.integration.conftest import requires_db


def _stub_emb(_):
    return [[0.0] * 1024]


@pytest.fixture()
def verified_source_id():
    db = SessionLocal()
    try:
        a = create_admin(
            db,
            email=f"llm_a_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com",
            password="Sup3rSecret!Pass",
        )
        b = create_admin(
            db,
            email=f"llm_b_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com",
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
            url="https://x.example/llm",
            title="LLM Tool Test",
            publisher="GCF",
        )
        source_service.verify(
            c, source_id=sid, verifier_id=b_id, embedding_func=_stub_emb
        )
    return sid


@pytest.fixture()
def pending_source_id():
    db = SessionLocal()
    try:
        a = create_admin(
            db,
            email=f"llm_p_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com",
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
            url="https://x.example/llmpending",
            title="Pending Test",
            publisher="GCF",
        )
    return sid


@requires_db
class TestCiteSourceRoute:
    def test_returns_200_for_verified(self, client, verified_source_id):
        r = client.post(
            "/internal/llm-tools/cite_source",
            json={"source_id": str(verified_source_id)},
        )
        assert r.status_code == 200, r.text
        assert r.json()["source"]["id"] == str(verified_source_id)

    def test_returns_422_for_pending(self, client, pending_source_id):
        r = client.post(
            "/internal/llm-tools/cite_source",
            json={"source_id": str(pending_source_id)},
        )
        assert r.status_code == 422
        assert r.json()["detail"]["code"] == "not_verified"

    def test_returns_404_when_unknown(self, client):
        r = client.post(
            "/internal/llm-tools/cite_source",
            json={"source_id": str(uuid.uuid4())},
        )
        assert r.status_code == 404

    def test_returns_422_for_malformed_input(self, client):
        r = client.post("/internal/llm-tools/cite_source", json={"wrong": "x"})
        assert r.status_code == 422


@requires_db
class TestSearchSourceRoute:
    def test_search_returns_only_verified(self, client, verified_source_id):
        r = client.post(
            "/internal/llm-tools/search_source",
            json={"query": "GCF", "k": 5},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        for it in body["items"]:
            assert it["verification_status"] == "verified"

    def test_search_rejects_empty_query(self, client):
        r = client.post(
            "/internal/llm-tools/search_source",
            json={"query": ""},
        )
        assert r.status_code == 422
