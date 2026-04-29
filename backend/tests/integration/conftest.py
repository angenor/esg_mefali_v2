"""Fixtures pour les tests d'intégration F02 (auth)."""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Generator

import pytest

# Désactive le rate limiter pour les tests
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


@pytest.fixture()
def unique_email() -> str:
    return f"itest_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"


@pytest.fixture()
def valid_password() -> str:
    return "Sup3rSecret!Pass"
