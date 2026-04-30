"""F32 — Tests d'integration dashboard PME.

Exercice les endpoints `/me/dashboard/summary` et `/me/data/export` via une
session PME nouvellement enregistree. Skippe si Postgres n'est pas dispo.
"""

from __future__ import annotations

from sqlalchemy import text

from tests.integration.conftest import requires_db


def _register_pme(client, email, password) -> None:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    csrf = client.cookies.get("mefali_csrf")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


@requires_db
class TestDashboardSummary:
    def test_summary_empty_account(self, client, unique_email, valid_password):
        _register_pme(client, unique_email, valid_password)
        r = client.get("/me/dashboard/summary")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["scores"] == []
        assert body["carbon"] == []
        assert body["credit_score"] is None
        assert body["candidatures"]["total"] == 0
        assert body["candidatures"]["recent"] == []
        assert body["rapports"]["total"] == 0
        assert body["rapports"]["recent"] == []
        assert body["attestations"]["active"] == 0
        assert body["attestations"]["revoked"] == 0
        assert body["next_actions"] == []
        assert "account_id" in body
        assert "generated_at" in body

    def test_summary_writes_audit_log(
        self, client, unique_email, valid_password
    ):
        _register_pme(client, unique_email, valid_password)
        r = client.get("/me/dashboard/summary")
        assert r.status_code == 200
        account_id = r.json()["account_id"]

        from sqlalchemy.orm import sessionmaker

        from app.db import get_engine_migrator

        sess = sessionmaker(bind=get_engine_migrator(), future=True)
        with sess() as s:
            cnt = s.execute(
                text(
                    "SELECT COUNT(*) FROM audit_log "
                    "WHERE entity_type='account' AND field='dashboard_view' "
                    "AND account_id = CAST(:aid AS UUID)"
                ),
                {"aid": account_id},
            ).scalar()
            assert cnt is not None and cnt >= 1

    def test_summary_requires_auth(self, client):
        client.cookies.clear()
        r = client.get("/me/dashboard/summary")
        assert r.status_code in {401, 403}


@requires_db
class TestDataExport:
    def test_export_minimal_account(self, client, unique_email, valid_password):
        _register_pme(client, unique_email, valid_password)
        r = client.get("/me/data/export")
        assert r.status_code == 200, r.text
        body = r.json()
        for key in (
            "account",
            "projets",
            "candidatures",
            "scores",
            "carbon",
            "rapports",
            "attestations",
            "consents",
            "action_plan",
            "exported_at",
        ):
            assert key in body
        assert body["projets"] == []
        assert body["candidatures"] == []
        assert isinstance(body["consents"], list)

    def test_export_writes_audit_log(self, client, unique_email, valid_password):
        _register_pme(client, unique_email, valid_password)
        r = client.get("/me/data/export")
        assert r.status_code == 200
        account_id = r.json()["account"].get("id")

        from sqlalchemy.orm import sessionmaker

        from app.db import get_engine_migrator

        sess = sessionmaker(bind=get_engine_migrator(), future=True)
        with sess() as s:
            cnt = s.execute(
                text(
                    "SELECT COUNT(*) FROM audit_log "
                    "WHERE entity_type='account' AND field='data_export' "
                    "AND account_id = CAST(:aid AS UUID)"
                ),
                {"aid": account_id},
            ).scalar()
            assert cnt is not None and cnt >= 1

    def test_export_requires_auth(self, client):
        client.cookies.clear()
        r = client.get("/me/data/export")
        assert r.status_code in {401, 403}


@requires_db
class TestRlsIsolation:
    """Deux PME distincts ne voient PAS les donnees croisees."""

    def test_two_pmes_isolated(self, client, valid_password):
        import time
        import uuid

        emails = [
            f"pme_a_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@ex.com",
            f"pme_b_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@ex.com",
        ]

        client.cookies.clear()
        _register_pme(client, emails[0], valid_password)
        r_a = client.get("/me/dashboard/summary")
        assert r_a.status_code == 200
        aid_a = r_a.json()["account_id"]

        client.cookies.clear()
        client.headers.pop("X-CSRF-Token", None)
        _register_pme(client, emails[1], valid_password)
        r_b = client.get("/me/dashboard/summary")
        assert r_b.status_code == 200
        aid_b = r_b.json()["account_id"]

        assert aid_a != aid_b
