"""F09 T015 — publish gate : refus si pas de source verified (FR-013)."""

from __future__ import annotations

import time
import uuid

from tests.integration.conftest import requires_db


def _uniq(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4].upper()}"


def _payload(code: str, source_ids: list[str]) -> dict:
    return {
        "code": code,
        "name": "Pub Gate",
        "definition": "x",
        "pillar": "E",
        "unite": "kg",
        "value_type": "numeric",
        "source_ids": source_ids,
    }


@requires_db
class TestPublishGate:
    def test_publish_without_sources_returns_422(self, admin_client):
        r = admin_client.post(
            "/admin/indicateurs/", json=_payload(_uniq("PG_NONE"), [])
        )
        obj = r.json()
        r2 = admin_client.post(
            f"/admin/indicateurs/{obj['id']}/publish", headers={"If-Match": '"v1"'}
        )
        assert r2.status_code == 422
        assert r2.json()["detail"]["code"] == "sources_not_verified"

    def test_publish_with_pending_source_returns_422(self, admin_client, pending_source):
        r = admin_client.post(
            "/admin/indicateurs/",
            json=_payload(_uniq("PG_PEND"), [pending_source["id"]]),
        )
        obj = r.json()
        r2 = admin_client.post(
            f"/admin/indicateurs/{obj['id']}/publish", headers={"If-Match": '"v1"'}
        )
        assert r2.status_code == 422
        assert r2.json()["detail"]["code"] == "sources_not_verified"

    def test_publish_with_verified_source_succeeds(self, admin_client, verified_source):
        r = admin_client.post(
            "/admin/indicateurs/",
            json=_payload(_uniq("PG_OK"), [verified_source["id"]]),
        )
        obj = r.json()
        r2 = admin_client.post(
            f"/admin/indicateurs/{obj['id']}/publish", headers={"If-Match": '"v1"'}
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["status"] == "published"
