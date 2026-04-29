"""F13 — Tests d'intégration des routes /me/chat/threads (US1, US2, US6)."""

from __future__ import annotations

from datetime import UTC, datetime

from .conftest import register_pme, requires_db


@requires_db
class TestThreadsCrud:
    def test_list_empty_then_create(self, client, unique_email, valid_password):
        register_pme(client, unique_email, valid_password)
        r = client.get("/me/chat/threads")
        assert r.status_code == 200, r.text
        assert r.json()["threads"] == []

        r = client.post("/me/chat/threads", json={})
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["archived"] is False
        assert body["title"]
        # Default title format
        today = datetime.now(UTC).strftime("%d/%m/%Y")
        assert today in body["title"]

        r = client.get("/me/chat/threads")
        assert r.status_code == 200
        assert len(r.json()["threads"]) == 1

    def test_archive_thread(self, client, unique_email, valid_password):
        register_pme(client, unique_email, valid_password)
        r = client.post("/me/chat/threads", json={})
        tid = r.json()["id"]

        r = client.delete(f"/me/chat/threads/{tid}")
        assert r.status_code == 204

        r = client.get("/me/chat/threads")
        ids = [t["id"] for t in r.json()["threads"]]
        assert tid not in ids

    def test_archive_unknown_returns_404(self, client, unique_email, valid_password):
        register_pme(client, unique_email, valid_password)
        import uuid
        bogus = str(uuid.uuid4())
        r = client.delete(f"/me/chat/threads/{bogus}")
        assert r.status_code == 404


@requires_db
class TestThreadsCrossTenant:
    def test_b_cannot_see_a_thread(
        self, client, client_b, unique_email, valid_password
    ):
        # PME A
        register_pme(client, unique_email, valid_password)
        r = client.post("/me/chat/threads", json={})
        tid = r.json()["id"]

        # PME B (autre email = autre account)
        import time
        import uuid
        email_b = f"f13b_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"
        register_pme(client_b, email_b, valid_password)

        # B ne doit voir aucun thread A
        r = client_b.get("/me/chat/threads")
        ids = [t["id"] for t in r.json()["threads"]]
        assert tid not in ids

        # B tente de lire les messages de A → 404
        r = client_b.get(f"/me/chat/threads/{tid}/messages")
        assert r.status_code == 404
