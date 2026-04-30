"""F33 - Tests admin url_patterns CRUD."""

from __future__ import annotations

import uuid

from sqlalchemy import text

from tests.integration.conftest import requires_db


def _register_and_promote_admin(client, email, password) -> None:
    """Cree un compte puis le passe en role admin via SQL direct."""
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    csrf = client.cookies.get("mefali_csrf")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf

    from sqlalchemy.orm import sessionmaker

    from app.db import get_engine_migrator

    sess = sessionmaker(bind=get_engine_migrator(), future=True)
    with sess() as s:
        s.execute(
            text("UPDATE account_user SET role = 'admin' WHERE email = :em"),
            {"em": email},
        )
        s.commit()


def _delete_pattern(pattern_id: str) -> None:
    from sqlalchemy.orm import sessionmaker

    from app.db import get_engine_migrator

    sess = sessionmaker(bind=get_engine_migrator(), future=True)
    with sess() as s:
        s.execute(
            text("DELETE FROM url_pattern WHERE id = CAST(:id AS UUID)"),
            {"id": pattern_id},
        )
        s.commit()


@requires_db
class TestAdminUrlPatterns:
    def test_requires_admin(self, client, unique_email, valid_password) -> None:
        client.post(
            "/auth/register",
            json={"email": unique_email, "password": valid_password},
        )
        csrf = client.cookies.get("mefali_csrf")
        if csrf:
            client.headers["X-CSRF-Token"] = csrf
        r = client.get("/admin/url-patterns")
        assert r.status_code in {401, 403}

    def test_create_and_list_pattern(
        self, client, unique_email, valid_password
    ) -> None:
        _register_and_promote_admin(client, unique_email, valid_password)
        r = client.post(
            "/admin/url-patterns",
            json={
                "pattern": "*adm-test-f33.org/*",
                "pattern_type": "wildcard",
                "nature": "fonds",
            },
        )
        assert r.status_code == 201, r.text
        new_id = r.json()["id"]
        try:
            assert r.json()["is_active"] is True
            r2 = client.get("/admin/url-patterns")
            assert r2.status_code == 200
            patterns = [it["pattern"] for it in r2.json()["items"]]
            assert "*adm-test-f33.org/*" in patterns
        finally:
            _delete_pattern(new_id)

    def test_create_invalid_regex_returns_422(
        self, client, unique_email, valid_password
    ) -> None:
        _register_and_promote_admin(client, unique_email, valid_password)
        r = client.post(
            "/admin/url-patterns",
            json={
                "pattern": "(unclosed",
                "pattern_type": "regex",
                "nature": "fonds",
            },
        )
        assert r.status_code == 422

    def test_patch_deactivate(self, client, unique_email, valid_password) -> None:
        _register_and_promote_admin(client, unique_email, valid_password)
        r = client.post(
            "/admin/url-patterns",
            json={
                "pattern": "*adm-patch-f33.org/*",
                "pattern_type": "wildcard",
                "nature": "intermediaire",
            },
        )
        assert r.status_code == 201
        new_id = r.json()["id"]
        try:
            rp = client.patch(
                f"/admin/url-patterns/{new_id}", json={"is_active": False}
            )
            assert rp.status_code == 200, rp.text
            assert rp.json()["is_active"] is False
        finally:
            _delete_pattern(new_id)

    def test_delete_soft(self, client, unique_email, valid_password) -> None:
        _register_and_promote_admin(client, unique_email, valid_password)
        r = client.post(
            "/admin/url-patterns",
            json={
                "pattern": "*adm-del-f33.org/*",
                "pattern_type": "wildcard",
                "nature": "fonds",
            },
        )
        new_id = r.json()["id"]
        try:
            rd = client.delete(f"/admin/url-patterns/{new_id}")
            assert rd.status_code == 204

            from sqlalchemy.orm import sessionmaker

            from app.db import get_engine_migrator

            sess = sessionmaker(bind=get_engine_migrator(), future=True)
            with sess() as s:
                row = s.execute(
                    text(
                        "SELECT is_active FROM url_pattern "
                        "WHERE id = CAST(:id AS UUID)"
                    ),
                    {"id": new_id},
                ).first()
                assert row is not None and row.is_active is False
        finally:
            _delete_pattern(new_id)

    def test_delete_not_found(self, client, unique_email, valid_password) -> None:
        _register_and_promote_admin(client, unique_email, valid_password)
        rd = client.delete(f"/admin/url-patterns/{uuid.uuid4()}")
        assert rd.status_code == 404

    def test_patch_not_found(self, client, unique_email, valid_password) -> None:
        _register_and_promote_admin(client, unique_email, valid_password)
        rp = client.patch(
            f"/admin/url-patterns/{uuid.uuid4()}", json={"is_active": False}
        )
        assert rp.status_code == 404
