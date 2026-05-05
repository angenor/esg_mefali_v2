"""F52 US5 — Tests d'intégration ``GET /me/extension/status``.

Couvre :
- Cas non détecté (aucun ping reçu).
- Cas détecté (ping récent).
- Cas expiré (ping > 24h).
"""

from __future__ import annotations

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


def _set_last_ping(*, user_id: str, account_id: str, when: datetime) -> None:
    sess = _engine_session()
    with sess() as s:
        # Upsert via SQL brut pour ne pas dépendre du service.
        s.execute(
            text(
                """
                INSERT INTO extension_ping
                  (id, account_id, user_id, extension_version,
                   user_agent_summary, last_ping_at, created_at)
                VALUES
                  (gen_random_uuid(), CAST(:aid AS UUID), CAST(:uid AS UUID),
                   '0.4.0', 'Chrome', :ts, :ts)
                ON CONFLICT (user_id) DO UPDATE
                  SET last_ping_at = EXCLUDED.last_ping_at
                """
            ),
            {"aid": account_id, "uid": user_id, "ts": when},
        )
        s.commit()


@requires_db
class TestExtensionStatus:
    def test_requires_auth(self, client) -> None:
        client.cookies.clear()
        r = client.get("/me/extension/status")
        assert r.status_code in {401, 403}

    def test_not_detected_when_no_ping(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.get("/me/extension/status")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["detected"] is False
        assert body["extension_version"] is None
        assert body["last_ping_at"] is None

    def test_detected_with_recent_ping(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        # Pose un ping récent
        client.post(
            "/me/extension/ping",
            json={
                "extension_version": "0.4.2",
                "user_agent_summary": "Chrome/124",
            },
        )
        r = client.get("/me/extension/status")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["detected"] is True
        assert body["extension_version"] == "0.4.2"
        assert body["last_ping_at"] is not None
        # Sanity check : me.id correspond bien
        assert me["id"]

    def test_not_detected_when_old_ping(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        # Insère un ping vieux de 2 jours
        old = datetime.now(UTC) - timedelta(days=2)
        _set_last_ping(
            user_id=me["id"], account_id=me["account_id"], when=old
        )
        r = client.get("/me/extension/status")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["detected"] is False
        # Mais last_ping_at reste exposé
        assert body["last_ping_at"] is not None
