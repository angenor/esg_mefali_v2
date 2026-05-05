"""F42 T049 — /auth/forgot-password : réponse strictement neutre (anti-énumération)."""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Generator

import pytest

os.environ.setdefault("DISABLE_RATE_LIMIT", "1")

from fastapi.testclient import TestClient  # noqa: E402

from app.main import app  # noqa: E402
from tests.conftest import DB_AVAILABLE  # noqa: E402

requires_db = pytest.mark.skipif(
    not DB_AVAILABLE,
    reason="Postgres indisponible — démarrer `docker compose up -d postgres`.",
)


@pytest.fixture()
def client() -> Generator[TestClient, None, None]:
    with TestClient(app) as c:
        yield c


@requires_db
def test_neutral_response_known_vs_unknown(client):
    pwd = "Sup3rSecret!Pass"
    known_email = f"known_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"
    client.post("/auth/register", json={"email": known_email, "password": pwd})
    client.cookies.clear()

    unknown_email = f"unknown_{uuid.uuid4().hex[:8]}@example.com"

    t0 = time.monotonic()
    rA = client.post("/auth/forgot-password", json={"email": known_email})
    tA = time.monotonic() - t0

    t1 = time.monotonic()
    rB = client.post("/auth/forgot-password", json={"email": unknown_email})
    tB = time.monotonic() - t1

    assert rA.status_code == rB.status_code == 202
    assert rA.json() == rB.json()
    assert rA.headers.get("content-type") == rB.headers.get("content-type")
    # Tolérance ± 200 ms pour absorber la variabilité CI/local
    assert abs(tA - tB) < 0.2
