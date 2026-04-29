"""F06 — fixtures for admin integration tests."""

from __future__ import annotations

import time
import uuid
from datetime import UTC, datetime
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from app.db import SessionLocal
from app.scripts.seed_admin import create_admin


@pytest.fixture()
def admin_client(client: TestClient, valid_password: str) -> TestClient:
    email = f"admin_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"
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
    # Stash for diagnostics
    client.headers.update({"X-Test-Admin-Email": email})
    return client


@pytest.fixture()
def pme_client(client: TestClient, unique_email: str, valid_password: str) -> TestClient:
    client.cookies.clear()
    r = client.post("/auth/register", json={"email": unique_email, "password": valid_password})
    assert r.status_code in (200, 201), r.text
    return client


@pytest.fixture()
def verified_source(admin_client: TestClient) -> dict[str, Any]:
    """Insert a verified source directly via SQL (admin context)."""
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_admin = 'true'"))
        sid = uuid.uuid4()
        # captured_by must reference an existing account_user; use the admin we just made.
        admin_id = db.execute(
            text("SELECT id FROM account_user WHERE role='admin' ORDER BY created_at DESC LIMIT 1")
        ).scalar()
        emb = "[" + ",".join("0.0" for _ in range(1024)) + "]"
        db.execute(
            text(
                """
                INSERT INTO source
                  (id, url, title, publisher, captured_at, captured_by,
                   verified_by, verified_at, embedding,
                   verification_status, status_version)
                VALUES
                  (CAST(:id AS UUID), :url, :title, :pub,
                   :now, CAST(:cap AS UUID),
                   CAST(:cap AS UUID), :now, CAST(:emb AS vector),
                   'verified', 1)
                """
            ),
            {
                "id": str(sid),
                "url": f"https://example.com/{sid}",
                "title": "Source verified",
                "pub": "ACME",
                "now": datetime.now(tz=UTC),
                "cap": str(admin_id),
                "emb": emb,
            },
        )
        db.commit()
        return {"id": str(sid)}
    finally:
        db.close()


@pytest.fixture()
def pending_source(admin_client: TestClient) -> dict[str, Any]:
    db = SessionLocal()
    try:
        db.execute(text("SET LOCAL app.is_admin = 'true'"))
        sid = uuid.uuid4()
        admin_id = db.execute(
            text("SELECT id FROM account_user WHERE role='admin' ORDER BY created_at DESC LIMIT 1")
        ).scalar()
        db.execute(
            text(
                """
                INSERT INTO source
                  (id, url, title, publisher, captured_at, captured_by,
                   verification_status, status_version)
                VALUES
                  (CAST(:id AS UUID), :url, :title, :pub,
                   :now, CAST(:cap AS UUID), 'pending', 1)
                """
            ),
            {
                "id": str(sid),
                "url": f"https://example.com/{sid}",
                "title": "Source pending",
                "pub": "ACME",
                "now": datetime.now(tz=UTC),
                "cap": str(admin_id),
            },
        )
        db.commit()
        return {"id": str(sid)}
    finally:
        db.close()
