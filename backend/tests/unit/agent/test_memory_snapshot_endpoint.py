"""F57 / US3 + US4 — Tests unit des routes ``/me/chat/threads/{id}/memory``.

Utilise ``FastAPI dependency_overrides`` + service patché.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_pme
from app.chat.memory.api import router as memory_router
from app.chat.memory.schemas import (
    EntityRef,
    ForgetMemoryResult,
    MemorySnapshotV2,
)
from app.chat.memory.service import ThreadMemoryNotFoundError
from app.db import get_db

pytestmark = pytest.mark.unit


def _fake_user(account_id: uuid.UUID | None = None):
    return SimpleNamespace(
        id=uuid.uuid4(),
        account_id=account_id or uuid.uuid4(),
        role="pme",
    )


@pytest.fixture()
def app_client() -> TestClient:
    app = FastAPI()
    app.include_router(memory_router)
    return TestClient(app, raise_server_exceptions=True)


# ----------------------- GET memory ----------------------------------------


def test_get_memory_returns_snapshot_v2(app_client, monkeypatch) -> None:
    user = _fake_user()
    snap = MemorySnapshotV2(
        total_messages=47,
        recent_messages_count=15,
        summary="Bullet 1\nBullet 2",
        vector_index_size=32,
        last_compaction_at=datetime(2026, 5, 4, 12, 34, 56, tzinfo=UTC),
        entities_referenced=[
            EntityRef(type="Entreprise", id=uuid.uuid4(), label="ACME"),
        ],
    )
    monkeypatch.setattr(
        "app.chat.memory.api.get_memory_snapshot", lambda db, **kw: snap
    )
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()

    tid = uuid.uuid4()
    r = app_client.get(f"/me/chat/threads/{tid}/memory")
    assert r.status_code == 200
    body = r.json()
    assert body["total_messages"] == 47
    assert body["recent_messages_count"] == 15
    assert body["summary"].startswith("Bullet")
    assert body["vector_index_size"] == 32
    assert body["last_compaction_at"].startswith("2026-05-04")
    assert len(body["entities_referenced"]) == 1
    assert body["entities_referenced"][0]["type"] == "Entreprise"


def test_get_memory_returns_404_cross_tenant(app_client, monkeypatch) -> None:
    user = _fake_user()

    def _raise(*a, **kw):
        raise ThreadMemoryNotFoundError("thread_not_found")

    monkeypatch.setattr("app.chat.memory.api.get_memory_snapshot", _raise)
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()

    tid = uuid.uuid4()
    r = app_client.get(f"/me/chat/threads/{tid}/memory")
    assert r.status_code == 404


def test_get_memory_summary_can_be_null(app_client, monkeypatch) -> None:
    """Thread sans compaction → summary=null, last_compaction_at=null."""
    user = _fake_user()
    snap = MemorySnapshotV2(
        total_messages=5,
        recent_messages_count=5,
        summary=None,
        vector_index_size=0,
        last_compaction_at=None,
        entities_referenced=[],
    )
    monkeypatch.setattr(
        "app.chat.memory.api.get_memory_snapshot", lambda db, **kw: snap
    )
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()

    r = app_client.get(f"/me/chat/threads/{uuid.uuid4()}/memory")
    assert r.status_code == 200
    body = r.json()
    assert body["summary"] is None
    assert body["last_compaction_at"] is None


# ----------------------- DELETE memory (forget RGPD) -----------------------


def test_delete_memory_returns_forget_result(app_client, monkeypatch) -> None:
    user = _fake_user()
    tid = uuid.uuid4()
    audit_id = uuid.uuid4()
    result = ForgetMemoryResult(
        thread_id=tid,
        embeddings_purged=32,
        summary_cleared=True,
        last_compaction_cleared=True,
        messages_kept_for_audit=47,
        agent_entity_memory_unchanged=True,
        audit_log_id=audit_id,
    )
    db_mock = MagicMock()
    monkeypatch.setattr(
        "app.chat.memory.api.forget_thread_memory", lambda db, **kw: result
    )
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: db_mock

    r = app_client.delete(f"/me/chat/threads/{tid}/memory")
    assert r.status_code == 200
    body = r.json()
    assert body["embeddings_purged"] == 32
    assert body["summary_cleared"] is True
    assert body["agent_entity_memory_unchanged"] is True
    assert body["audit_log_id"] == str(audit_id)


def test_delete_memory_returns_404_if_thread_not_found(
    app_client, monkeypatch
) -> None:
    user = _fake_user()

    def _raise(*a, **kw):
        raise ThreadMemoryNotFoundError("thread_not_found")

    monkeypatch.setattr("app.chat.memory.api.forget_thread_memory", _raise)
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()

    r = app_client.delete(f"/me/chat/threads/{uuid.uuid4()}/memory")
    assert r.status_code == 404


def test_delete_memory_idempotent_zero_purged(
    app_client, monkeypatch
) -> None:
    """Deuxième DELETE → 200 idempotent avec embeddings_purged=0."""
    user = _fake_user()
    tid = uuid.uuid4()
    result = ForgetMemoryResult(
        thread_id=tid,
        embeddings_purged=0,
        summary_cleared=False,
        last_compaction_cleared=False,
        messages_kept_for_audit=0,
        agent_entity_memory_unchanged=True,
        audit_log_id=None,
    )
    monkeypatch.setattr(
        "app.chat.memory.api.forget_thread_memory", lambda db, **kw: result
    )
    app_client.app.dependency_overrides[get_current_pme] = lambda: user
    app_client.app.dependency_overrides[get_db] = lambda: MagicMock()

    r = app_client.delete(f"/me/chat/threads/{tid}/memory")
    assert r.status_code == 200
    assert r.json()["embeddings_purged"] == 0
