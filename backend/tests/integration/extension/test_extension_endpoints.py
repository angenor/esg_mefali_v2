"""F33 - Tests d'integration des endpoints extension PME."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from sqlalchemy import text

from tests.integration.conftest import requires_db


def _register_pme(client, email, password) -> None:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    csrf = client.cookies.get("mefali_csrf")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


def _engine_session():
    from sqlalchemy.orm import sessionmaker

    from app.db import get_engine_migrator

    return sessionmaker(bind=get_engine_migrator(), future=True)


def _cleanup_pattern(new_id: uuid.UUID) -> None:
    sess = _engine_session()
    with sess() as s:
        s.execute(
            text("DELETE FROM url_pattern WHERE id = CAST(:id AS UUID)"),
            {"id": str(new_id)},
        )
        s.commit()


@requires_db
class TestUrlPatternsRoute:
    def test_requires_auth(self, client) -> None:
        client.cookies.clear()
        r = client.get("/extension/url-patterns")
        assert r.status_code in {401, 403}

    def test_returns_empty_for_pme(self, client, unique_email, valid_password) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.get("/extension/url-patterns")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "items" in body and "updated_at" in body

    def test_lists_active_pattern_without_offre(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        sess = _engine_session()
        new_id = uuid.uuid4()
        with sess() as s:
            now = datetime.now(UTC)
            s.execute(
                text(
                    """
                    INSERT INTO url_pattern (id, pattern, pattern_type, nature,
                      is_active, created_at, updated_at)
                    VALUES (:id, :pat, 'wildcard', 'fonds', TRUE, :ts, :ts)
                    """
                ),
                {"id": str(new_id), "pat": "*example-test-f33.org/*", "ts": now},
            )
            s.commit()
        try:
            r = client.get("/extension/url-patterns")
            assert r.status_code == 200
            patterns = [it["pattern"] for it in r.json()["items"]]
            assert "*example-test-f33.org/*" in patterns
        finally:
            _cleanup_pattern(new_id)

    def test_excludes_inactive(self, client, unique_email, valid_password) -> None:
        _register_pme(client, unique_email, valid_password)
        sess = _engine_session()
        new_id = uuid.uuid4()
        with sess() as s:
            now = datetime.now(UTC)
            s.execute(
                text(
                    """
                    INSERT INTO url_pattern (id, pattern, pattern_type, nature,
                      is_active, created_at, updated_at)
                    VALUES (:id, :pat, 'wildcard', 'fonds', FALSE, :ts, :ts)
                    """
                ),
                {"id": str(new_id), "pat": "*inactive-test-f33.org/*", "ts": now},
            )
            s.commit()
        try:
            r = client.get("/extension/url-patterns")
            assert r.status_code == 200
            patterns = [it["pattern"] for it in r.json()["items"]]
            assert "*inactive-test-f33.org/*" not in patterns
        finally:
            _cleanup_pattern(new_id)


@requires_db
class TestProfileSummaryRoute:
    def test_requires_auth(self, client) -> None:
        client.cookies.clear()
        r = client.get("/extension/profile-summary")
        assert r.status_code in {401, 403}

    def test_returns_minimal_summary(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.get("/extension/profile-summary")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "account_id" in body
        assert "generated_at" in body
        import json as _json

        assert len(_json.dumps(body).encode("utf-8")) <= 4096


@requires_db
class TestSuggestFieldRoute:
    def test_requires_auth(self, client) -> None:
        client.cookies.clear()
        r = client.post(
            "/extension/suggest-field",
            json={"field_label": "Description", "field_max_length": 200},
        )
        assert r.status_code in {401, 403}

    def test_returns_fallback_or_llm(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.post(
            "/extension/suggest-field",
            json={"field_label": "Description du projet", "field_max_length": 100},
        )
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["source"] in ("llm", "fallback")
        assert 1 <= body["length"] <= 100
        assert isinstance(body["text"], str) and len(body["text"]) <= 100

    def test_validation_invalid_max_length(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.post(
            "/extension/suggest-field",
            json={"field_label": "X", "field_max_length": 0},
        )
        assert r.status_code == 422


@requires_db
class TestFieldMappingsRoute:
    def test_requires_auth(self, client) -> None:
        client.cookies.clear()
        r = client.get("/extension/field-mappings")
        assert r.status_code in {401, 403}

    def test_returns_empty(self, client, unique_email, valid_password) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.get("/extension/field-mappings")
        assert r.status_code == 200
        assert "items" in r.json()
