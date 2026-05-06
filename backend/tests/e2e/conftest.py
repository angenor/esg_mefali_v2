"""Fixtures partagées pour les tests E2E F58 (guardrails, kill-switch, minimal mode, eval).

Pattern identique aux conftest chat/ et integration/ ; fournit client,
unique_email, valid_password, admin_client et chat_message pour tous les
fichiers du répertoire e2e/.

Note : les tests guardrails/minimal_mode utilisent le vrai endpoint de chat
``POST /me/chat/threads/{thread_id}/messages`` (SSE), pas /chat/stream qui
n'existe pas dans l'app. L'helper ``chat_message`` gère auth + CSRF + thread.
"""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Generator
from typing import Any

import pytest

os.environ.setdefault("DISABLE_RATE_LIMIT", "1")
os.environ.setdefault("LLM_STUB", "1")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def unique_email() -> str:
    return f"e2e_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}@example.com"


@pytest.fixture()
def valid_password() -> str:
    return "Sup3rSecret!Pass"


@pytest.fixture()
def admin_client(client: TestClient, valid_password: str) -> TestClient:
    from app.db import SessionLocal
    from app.scripts.seed_admin import create_admin

    email = f"e2e_admin_{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}@example.com"
    db = SessionLocal()
    try:
        create_admin(db, email=email, password=valid_password)
        db.commit()
    finally:
        db.close()
    client.cookies.clear()
    r = client.post("/auth/login", json={"email": email, "password": valid_password})
    assert r.status_code == 200, r.text
    csrf = client.cookies.get("mefali_csrf")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    return client


def _register_login_csrf(
    client: TestClient, email: str, password: str
) -> None:
    """Enregistre, connecte et injecte le header X-CSRF-Token dans le client."""
    client.cookies.clear()
    client.post("/auth/register", json={"email": email, "password": password})
    client.post("/auth/login", json={"email": email, "password": password})
    csrf = client.cookies.get("mefali_csrf")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


def _send_chat_message(client: TestClient, message: str) -> Any:
    """Crée un thread et envoie un message ; retourne la Response SSE."""
    r_thread = client.post("/me/chat/threads", json={})
    assert r_thread.status_code in (200, 201), f"thread creation failed: {r_thread.text}"
    thread_id = r_thread.json()["id"]
    return client.post(
        f"/me/chat/threads/{thread_id}/messages",
        json={"content": message, "context_json": {}},
    )
