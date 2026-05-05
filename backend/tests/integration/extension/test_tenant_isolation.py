"""F52 US4 NFR-003 — Cloisonnement multi-tenant du sidepanel-context."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

from sqlalchemy import text

from tests.integration.conftest import requires_db


def _register_pme(client, email, password) -> dict:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    csrf = client.cookies.get("mefali_csrf")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    me = client.get("/me")
    assert me.status_code == 200
    return me.json()


def _engine_session():
    from sqlalchemy.orm import sessionmaker

    from app.db import get_engine_migrator

    return sessionmaker(bind=get_engine_migrator(), future=True)


def _insert_candidature(
    *, account_id: str, projet_id: uuid.UUID, offre_id: uuid.UUID
) -> uuid.UUID:
    cid = uuid.uuid4()
    now = datetime.now(UTC).replace(tzinfo=None)
    sess = _engine_session()
    with sess() as s:
        s.execute(
            text(
                """
                INSERT INTO candidature
                  (id, account_id, projet_id, offre_id, statut,
                   version, created_at, updated_at)
                VALUES
                  (CAST(:id AS UUID), CAST(:aid AS UUID),
                   CAST(:pid AS UUID), CAST(:oid AS UUID),
                   'en_cours', 1, :ts, :ts)
                """
            ),
            {
                "id": str(cid),
                "aid": account_id,
                "pid": str(projet_id),
                "oid": str(offre_id),
                "ts": now,
            },
        )
        s.commit()
    return cid


@requires_db
class TestTenantIsolation:
    def test_account_a_does_not_see_account_b(
        self, client, valid_password
    ) -> None:
        # Compte A
        a_email = f"a_{uuid.uuid4().hex[:8]}@example.com"
        me_a = _register_pme(client, a_email, valid_password)

        # Logout pour déconnecter A
        client.post("/auth/logout")
        client.cookies.clear()
        client.headers.pop("X-CSRF-Token", None)

        # Compte B
        b_email = f"b_{uuid.uuid4().hex[:8]}@example.com"
        _register_pme(client, b_email, valid_password)

        # Côté B : récupérer le contexte sidepanel
        r_b = client.get(
            "/me/extension/sidepanel-context",
            params={"host": "boad.org", "path": "/x"},
        )
        assert r_b.status_code == 200
        body_b = r_b.json()

        # Aucun item appartenant à A ne doit apparaître
        a_id = me_a["account_id"]
        for item in body_b.get("active_candidatures", []):
            assert "account_id" not in item or item.get("account_id") != a_id
        # Vérification additionnelle : on n'expose pas account_id dans le contrat
        if body_b["active_candidatures"]:
            for item in body_b["active_candidatures"]:
                assert "account_id" not in item

    def test_extension_ping_isolated(
        self, client, valid_password
    ) -> None:
        a_email = f"a_{uuid.uuid4().hex[:8]}@example.com"
        me_a = _register_pme(client, a_email, valid_password)
        r_a = client.post(
            "/me/extension/ping",
            json={"extension_version": "0.4.0", "user_agent_summary": "Chrome A"},
        )
        assert r_a.status_code == 204

        client.post("/auth/logout")
        client.cookies.clear()
        client.headers.pop("X-CSRF-Token", None)

        b_email = f"b_{uuid.uuid4().hex[:8]}@example.com"
        _register_pme(client, b_email, valid_password)
        r_b = client.post(
            "/me/extension/ping",
            json={"extension_version": "0.4.2", "user_agent_summary": "Chrome B"},
        )
        assert r_b.status_code == 204

        # Vérifie que A et B ont chacun un row distinct
        sess = _engine_session()
        with sess() as s:
            count_a = s.execute(
                text(
                    "SELECT COUNT(*) FROM extension_ping "
                    "WHERE user_id = CAST(:uid AS UUID)"
                ),
                {"uid": me_a["id"]},
            ).scalar()
            assert count_a == 1
