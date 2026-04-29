"""F13 — Tests d'intégration POST/GET messages (US2, US3, US5)."""

from __future__ import annotations

from .conftest import register_pme, requires_db


@requires_db
class TestPostMessage:
    def test_send_message_streams_and_persists(self, client, unique_email, valid_password):
        register_pme(client, unique_email, valid_password)
        tid = client.post("/me/chat/threads", json={}).json()["id"]

        with client.stream(
            "POST",
            f"/me/chat/threads/{tid}/messages",
            json={"content": "bonjour", "context_json": {"page": "/"}},
        ) as response:
            assert response.status_code == 200
            assert "text/event-stream" in response.headers.get("content-type", "")
            chunks = list(response.iter_text())
        body = "".join(chunks)
        assert "event: text_delta" in body
        assert "event: message_done" in body
        assert "[F13 stub" in body  # stub mode in tests

        # Both user and assistant messages persisted
        r = client.get(f"/me/chat/threads/{tid}/messages")
        msgs = r.json()["messages"]
        roles = [m["role"] for m in msgs]
        assert "user" in roles
        assert "assistant" in roles

    def test_user_message_carries_context_json(self, client, unique_email, valid_password):
        register_pme(client, unique_email, valid_password)
        tid = client.post("/me/chat/threads", json={}).json()["id"]
        ctx = {"page": "/profil/projets/abc", "entity_type": "projet", "entity_id": "abc"}
        with client.stream(
            "POST",
            f"/me/chat/threads/{tid}/messages",
            json={"content": "hello", "context_json": ctx},
        ) as r:
            list(r.iter_text())

        r = client.get(f"/me/chat/threads/{tid}/messages")
        msgs = r.json()["messages"]
        user_row = next(m for m in msgs if m["role"] == "user")
        assert user_row["context_json"]["page"] == ctx["page"]
        assert user_row["context_json"]["entity_id"] == "abc"

    def test_extra_context_field_returns_422(self, client, unique_email, valid_password):
        register_pme(client, unique_email, valid_password)
        tid = client.post("/me/chat/threads", json={}).json()["id"]
        r = client.post(
            f"/me/chat/threads/{tid}/messages",
            json={"content": "x", "context_json": {"page": "/", "secret": "leak"}},
        )
        assert r.status_code == 422

    def test_post_to_archived_returns_409(self, client, unique_email, valid_password):
        register_pme(client, unique_email, valid_password)
        tid = client.post("/me/chat/threads", json={}).json()["id"]
        client.delete(f"/me/chat/threads/{tid}")
        r = client.post(
            f"/me/chat/threads/{tid}/messages",
            json={"content": "hi", "context_json": {"page": "/"}},
        )
        assert r.status_code == 409
        assert r.json()["detail"] == "thread_archived"

    def test_oversized_content_rejected(self, client, unique_email, valid_password):
        register_pme(client, unique_email, valid_password)
        tid = client.post("/me/chat/threads", json={}).json()["id"]
        big = "x" * (33 * 1024)  # > 32 KB
        r = client.post(
            f"/me/chat/threads/{tid}/messages",
            json={"content": big, "context_json": {"page": "/"}},
        )
        assert r.status_code in (413, 422)
