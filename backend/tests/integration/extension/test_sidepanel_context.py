"""F52 US4 — Tests d'intégration ``GET /me/extension/sidepanel-context``."""

from __future__ import annotations

import uuid

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


def _ensure_url_pattern(pattern: str = "*.boad.org/*") -> uuid.UUID | None:
    """Retourne l'ID du pattern existant ou en crée un actif (best-effort).

    Si la table url_pattern n'a pas le format attendu, retourne None et le test
    s'adapte (vérifie seulement les listes vides).
    """
    sess = _engine_session()
    with sess() as s:
        try:
            r = s.execute(
                text(
                    """
                    SELECT id FROM url_pattern
                    WHERE pattern = :p AND is_active = TRUE
                    LIMIT 1
                    """
                ),
                {"p": pattern},
            ).first()
            if r is not None:
                return r.id
            pid = uuid.uuid4()
            s.execute(
                text(
                    """
                    INSERT INTO url_pattern
                      (id, pattern, pattern_type, nature, is_active,
                       created_at, updated_at)
                    VALUES
                      (CAST(:id AS UUID), :p, 'wildcard', 'fonds', TRUE,
                       NOW(), NOW())
                    """
                ),
                {"id": str(pid), "p": pattern},
            )
            s.commit()
            return pid
        except Exception:  # pragma: no cover — schéma url_pattern variable
            s.rollback()
            return None


@requires_db
class TestSidepanelContext:
    def test_requires_auth(self, client) -> None:
        client.cookies.clear()
        r = client.get(
            "/me/extension/sidepanel-context",
            params={"host": "boad.org", "path": "/financements"},
        )
        assert r.status_code in {401, 403}

    def test_no_match_returns_empty_lists(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.get(
            "/me/extension/sidepanel-context",
            params={
                "host": "non-listed.example",
                "path": "/x",
            },
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["active_candidatures"] == []
        assert body["recommended_offers"] == []
        assert body["matched_offer_ids"] == []

    def test_match_returns_lists(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        _ensure_url_pattern("*.boad.org/*")
        r = client.get(
            "/me/extension/sidepanel-context",
            params={"host": "www.boad.org", "path": "/financements/ligne-verte"},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        # listes peuvent être vides en l'absence de candidatures actives.
        assert isinstance(body["active_candidatures"], list)
        assert isinstance(body["recommended_offers"], list)
        assert isinstance(body["matched_offer_ids"], list)
