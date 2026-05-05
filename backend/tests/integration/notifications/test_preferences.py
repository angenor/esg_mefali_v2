"""F52 US2 — Tests d'intégration ``/me/notification-preferences``.

Couvre : auto-instanciation des défauts à la première lecture, batch atomique,
audit log écrit pour chaque mutation.
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
    return client.get("/me").json()


def _engine_session():
    from sqlalchemy.orm import sessionmaker

    from app.db import get_engine_migrator

    return sessionmaker(bind=get_engine_migrator(), future=True)


@requires_db
class TestPreferences:
    def test_get_auto_instantiates_defaults(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.get("/me/notification-preferences")
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        # 5 kinds × 2 channels = 10 rows par défaut.
        assert len(items) >= 10
        assert all(it["enabled"] for it in items)

    def test_patch_updates_subset_atomically(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        # bootstrap
        client.get("/me/notification-preferences")

        body = {
            "updates": [
                {
                    "kind": "deadline_j_minus_30",
                    "channel": "email",
                    "enabled": False,
                },
                {
                    "kind": "offre_recommandee",
                    "channel": "email",
                    "enabled": False,
                },
            ]
        }
        r = client.patch("/me/notification-preferences", json=body)
        assert r.status_code == 200, r.text
        items = r.json()["items"]
        flat = {(it["kind"], it["channel"]): it["enabled"] for it in items}
        assert flat[("deadline_j_minus_30", "email")] is False
        assert flat[("offre_recommandee", "email")] is False
        # in_app reste true (non touché).
        assert flat[("deadline_j_minus_30", "in_app")] is True

    def test_patch_rejects_invalid_kind(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        body = {"updates": [{"kind": "NOPE", "channel": "email", "enabled": True}]}
        r = client.patch("/me/notification-preferences", json=body)
        assert r.status_code in {400, 422}

    def test_patch_writes_audit_log(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        client.get("/me/notification-preferences")

        body = {
            "updates": [
                {
                    "kind": "deadline_j_minus_7",
                    "channel": "in_app",
                    "enabled": False,
                }
            ]
        }
        r = client.patch("/me/notification-preferences", json=body)
        assert r.status_code == 200

        sess = _engine_session()
        with sess() as s:
            count = s.execute(
                text(
                    "SELECT COUNT(*) FROM audit_log "
                    "WHERE entity_type = 'notification_preference' "
                    "  AND field = 'enabled' "
                    "  AND new_value::text LIKE '%false%'"
                )
            ).scalar_one()
            assert int(count) >= 1
