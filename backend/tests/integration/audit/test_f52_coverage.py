"""F52 NFR-003 / FR-013 — couverture audit log des mutations sensibles.

Vérifie qu'un row ``audit_log`` est écrit pour chaque mutation listée dans
``data-model.md`` (table ``Audit (P3)``). Les flux concernés :

- mise à jour préférence notifications (``notification_preference.enabled``) ;
- demande de modification e-mail (``account_user.email_pending``) ;
- demande de suppression compte (``account_deletion_request.status``) ;
- annulation de suppression (``account_deletion_request.status``) ;
- révocation session (``account_user_session.revoked_at``).

L'audit est un best-effort (l'appelant ne plante pas si l'écriture échoue),
mais en environnement nominal les rows DOIVENT être présents.
"""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import text

from tests.integration.conftest import requires_db


def _register_pme(client, email: str, password: str) -> dict:
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


def _seed_entreprise(account_id: str, raison_sociale: str) -> None:
    sess = _engine_session()
    with sess() as s:
        now = datetime.now(UTC).replace(tzinfo=None)
        s.execute(
            text(
                """
                INSERT INTO entreprise
                  (id, account_id, name, version, created_at, updated_at)
                VALUES
                  (gen_random_uuid(), CAST(:aid AS UUID), :rs, 1, :ts, :ts)
                """
            ),
            {"aid": account_id, "rs": raison_sociale, "ts": now},
        )
        s.commit()


def _audit_count(account_id: str, *, entity: str, field: str | None = None) -> int:
    sess = _engine_session()
    with sess() as s:
        q = (
            "SELECT COUNT(*) FROM audit_log "
            "WHERE account_id = CAST(:aid AS UUID) AND entity_type = :ent"
        )
        params: dict[str, object] = {"aid": account_id, "ent": entity}
        if field is not None:
            q += " AND field = :field"
            params["field"] = field
        row = s.execute(text(q), params).first()
        return int(row[0]) if row else 0


@requires_db
class TestF52AuditCoverage:
    def test_preferences_patch_writes_audit(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        # bootstrap defaults
        client.get("/me/notification-preferences")
        before = _audit_count(
            me["account_id"], entity="notification_preference", field="enabled"
        )
        r = client.patch(
            "/me/notification-preferences",
            json={
                "updates": [
                    {
                        "kind": "deadline_j_minus_30",
                        "channel": "email",
                        "enabled": False,
                    }
                ]
            },
        )
        assert r.status_code == 200, r.text
        after = _audit_count(
            me["account_id"], entity="notification_preference", field="enabled"
        )
        assert after >= before + 1, "audit log manquant pour notification_preference"

    def test_email_change_writes_audit(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        before = _audit_count(
            me["account_id"], entity="account_user", field="email_pending"
        )
        r = client.post(
            "/me/email-change",
            json={"new_email": f"new-{unique_email}"},
        )
        # 200 ou 202 selon implémentation
        assert r.status_code in (200, 201, 202), r.text
        after = _audit_count(
            me["account_id"], entity="account_user", field="email_pending"
        )
        assert after >= before + 1, "audit log manquant pour email_pending"

    def test_account_deletion_create_and_cancel_write_audit(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        _seed_entreprise(me["account_id"], "ACME SARL")
        before = _audit_count(
            me["account_id"], entity="account_deletion_request", field="status"
        )
        # création
        r1 = client.post(
            "/me/account-deletion",
            json={"confirmation_text": "ACME SARL"},
        )
        assert r1.status_code == 201, r1.text
        mid = _audit_count(
            me["account_id"], entity="account_deletion_request", field="status"
        )
        assert mid >= before + 1, "audit log manquant pour la création"
        # annulation
        r2 = client.delete("/me/account-deletion")
        assert r2.status_code in (200, 204), r2.text
        after = _audit_count(
            me["account_id"], entity="account_deletion_request", field="status"
        )
        assert after >= mid + 1, "audit log manquant pour l'annulation"

    def test_session_revoke_writes_audit(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        list_r = client.get("/me/sessions")
        assert list_r.status_code == 200, list_r.text
        sessions = list_r.json().get("items") or list_r.json().get("sessions") or []
        # Ne pas tenter de révoquer la session courante (l'API doit refuser).
        target = next((s for s in sessions if not s.get("is_current")), None)
        if target is None:
            # Forge une session annexe via insert direct si l'API ne renvoie qu'une row.
            sess = _engine_session()
            with sess() as s:
                s.execute(
                    text(
                        """
                        INSERT INTO refresh_tokens
                          (id, account_id, user_id, token_hash, created_at,
                           expires_at)
                        VALUES
                          (gen_random_uuid(), CAST(:aid AS UUID),
                           CAST(:uid AS UUID), :h, now(), now() + interval '7 days')
                        RETURNING id
                        """
                    ),
                    {
                        "aid": me["account_id"],
                        "uid": me["id"],
                        "h": "stub-hash-coverage",
                    },
                )
                s.commit()
            list_r = client.get("/me/sessions")
            sessions = list_r.json().get("items") or list_r.json().get("sessions") or []
            target = next((s for s in sessions if not s.get("is_current")), None)

        assert target, "Pas de session révocable disponible pour le test"
        before = _audit_count(
            me["account_id"], entity="account_user_session", field="revoked_at"
        )
        before_alt = _audit_count(
            me["account_id"], entity="refresh_tokens", field="revoked_at"
        )
        r = client.delete(f"/me/sessions/{target['id']}")
        assert r.status_code in (200, 204), r.text
        after = _audit_count(
            me["account_id"], entity="account_user_session", field="revoked_at"
        )
        after_alt = _audit_count(
            me["account_id"], entity="refresh_tokens", field="revoked_at"
        )
        assert (after >= before + 1) or (
            after_alt >= before_alt + 1
        ), "audit log manquant pour la révocation de session"
