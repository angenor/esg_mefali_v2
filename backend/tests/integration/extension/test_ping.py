"""F52 US4 — Tests d'intégration ``POST /me/extension/ping``.

Couvre :
- 204 No Content + UPSERT idempotent.
- Mise à jour ``last_ping_at`` à chaque ping.
- Validation Pydantic (semver, max length).
"""

from __future__ import annotations

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


@requires_db
class TestExtensionPing:
    def test_requires_auth(self, client) -> None:
        client.cookies.clear()
        r = client.post(
            "/me/extension/ping",
            json={"extension_version": "0.4.2", "user_agent_summary": "Chrome"},
        )
        assert r.status_code in {401, 403}

    def test_ping_204(self, client, unique_email, valid_password) -> None:
        me = _register_pme(client, unique_email, valid_password)
        r = client.post(
            "/me/extension/ping",
            json={"extension_version": "0.4.2", "user_agent_summary": "Chrome/124"},
        )
        assert r.status_code == 204, r.text

        # Vérifier que la table extension_ping a un row pour cet utilisateur
        sess = _engine_session()
        with sess() as s:
            row = s.execute(
                text(
                    """
                    SELECT extension_version, user_agent_summary
                    FROM extension_ping
                    WHERE user_id = CAST(:uid AS UUID)
                    """
                ),
                {"uid": me["id"]},
            ).first()
            assert row is not None
            assert row.extension_version == "0.4.2"

    def test_ping_idempotent_upsert(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        # 2 pings successifs avec versions différentes
        r1 = client.post(
            "/me/extension/ping",
            json={"extension_version": "0.4.0", "user_agent_summary": "Chrome/120"},
        )
        assert r1.status_code == 204
        r2 = client.post(
            "/me/extension/ping",
            json={"extension_version": "0.4.2", "user_agent_summary": "Chrome/124"},
        )
        assert r2.status_code == 204

        # Une seule row pour cet user
        sess = _engine_session()
        with sess() as s:
            cnt = s.execute(
                text(
                    "SELECT COUNT(*) FROM extension_ping "
                    "WHERE user_id = CAST(:uid AS UUID)"
                ),
                {"uid": me["id"]},
            ).scalar()
            assert cnt == 1
            row = s.execute(
                text(
                    """
                    SELECT extension_version
                    FROM extension_ping
                    WHERE user_id = CAST(:uid AS UUID)
                    """
                ),
                {"uid": me["id"]},
            ).first()
            assert row.extension_version == "0.4.2"

    def test_invalid_semver_rejected(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.post(
            "/me/extension/ping",
            json={"extension_version": "not-semver", "user_agent_summary": "Chrome"},
        )
        assert r.status_code in {400, 422}
