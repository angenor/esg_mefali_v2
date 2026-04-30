"""F32 — Tests unitaires du routeur (dependency override + audit best-effort)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from app.auth.dependencies import get_current_pme
from app.db import get_db
from app.main import app


def _empty_db_mock() -> MagicMock:
    sess = MagicMock()

    def _exec(*_args, **_kwargs):
        result = MagicMock()
        result.all.return_value = []
        result.first.return_value = None
        result.scalar.return_value = 0
        return result

    sess.execute.side_effect = _exec
    return sess


@pytest.fixture()
def client_with_pme() -> TestClient:
    """A TestClient with a PME user injected via dependency override."""
    fake_user = SimpleNamespace(
        id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        role="pme",
        email="pme@example.com",
    )

    app.dependency_overrides[get_current_pme] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: _empty_db_mock()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_pme, None)
        app.dependency_overrides.pop(get_db, None)


@pytest.fixture()
def client_pme_no_account() -> TestClient:
    fake_user = SimpleNamespace(
        id=uuid.uuid4(),
        account_id=None,
        role="pme",
        email="pme@example.com",
    )
    app.dependency_overrides[get_current_pme] = lambda: fake_user
    app.dependency_overrides[get_db] = lambda: _empty_db_mock()
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_current_pme, None)
        app.dependency_overrides.pop(get_db, None)


class TestSummaryEndpoint:
    def test_summary_returns_200_with_overrides(
        self, client_with_pme: TestClient
    ) -> None:
        with patch("app.audit.helper.record_audit", return_value=None):
            r = client_with_pme.get("/me/dashboard/summary")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["scores"] == []
        assert body["candidatures"]["total"] == 0

    def test_summary_403_when_no_account(
        self, client_pme_no_account: TestClient
    ) -> None:
        r = client_pme_no_account.get("/me/dashboard/summary")
        assert r.status_code == 403
        assert r.json()["detail"]["code"] == "no_account"


class TestExportEndpoint:
    def test_export_returns_200_with_overrides(
        self, client_with_pme: TestClient
    ) -> None:
        with patch("app.audit.helper.record_audit", return_value=None):
            r = client_with_pme.get("/me/data/export")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["projets"] == []
        assert body["candidatures"] == []
        assert "exported_at" in body

    def test_export_403_when_no_account(
        self, client_pme_no_account: TestClient
    ) -> None:
        r = client_pme_no_account.get("/me/data/export")
        assert r.status_code == 403


class TestAuditBestEffort:
    """L'echec d'audit ne doit PAS faire echouer la requete."""

    def test_summary_audit_failure_swallowed(
        self, client_with_pme: TestClient
    ) -> None:
        with patch(
            "app.audit.helper.record_audit", side_effect=RuntimeError("boom")
        ):
            r = client_with_pme.get("/me/dashboard/summary")
        assert r.status_code == 200

    def test_export_audit_failure_swallowed(
        self, client_with_pme: TestClient
    ) -> None:
        with patch(
            "app.audit.helper.record_audit", side_effect=RuntimeError("boom")
        ):
            r = client_with_pme.get("/me/data/export")
        assert r.status_code == 200


def test_safe_audit_handles_rollback_failure() -> None:
    """Cover the rollback try/except branch in _safe_audit."""
    from app.dashboard.router import _safe_audit

    db = MagicMock()
    db.rollback.side_effect = RuntimeError("rollback failed")

    with patch(
        "app.audit.helper.record_audit", side_effect=RuntimeError("audit failed")
    ):
        _safe_audit(
            db, account_id=uuid.uuid4(), user_id=uuid.uuid4(), action="test_action"
        )


def test_imports_smoke() -> None:
    from app.dashboard import router as r

    assert r.router is not None
    assert datetime.now(tz=UTC) is not None
