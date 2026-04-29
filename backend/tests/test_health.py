"""Tests endpoint /health (T011, T012)."""

from __future__ import annotations

from fastapi.testclient import TestClient
from sqlalchemy.exc import OperationalError

from tests.conftest import requires_db


@requires_db
def test_health_ok_returns_200(monkeypatch):
    """T011 — /health retourne 200 + body {status: ok, db: ok} quand DB up."""
    from app.main import app

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "ok"
        assert body["db"] == "ok"


def test_health_db_unreachable_returns_503(monkeypatch):
    """T012 — quand la session DB raise OperationalError → 503."""
    from app import db as db_module
    from app.main import app

    class _BrokenSession:
        def execute(self, *args, **kwargs):
            raise OperationalError("SELECT 1", params=None, orig=Exception("boom"))

        def close(self):
            pass

    def _broken_session_local():
        return _BrokenSession()

    monkeypatch.setattr(db_module, "SessionLocal", _broken_session_local)

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 503
        body = r.json()
        assert body["status"] == "degraded"
        assert body["db"] == "unreachable"
