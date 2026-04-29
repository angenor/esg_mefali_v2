"""F06 T026 — ETag/If-Match concurrency + new version on published edit."""

from __future__ import annotations

from tests.integration.conftest import requires_db


def _create(client, source_id):
    r = client.post(
        "/admin/demo_indicator/",
        json={
            "name": "Indicator A",
            "publisher": "Pub",
            "external_id": f"EXT-{source_id[:8]}",
            "source_id": source_id,
        },
    )
    assert r.status_code == 201
    return r.json()


@requires_db
class TestEtagConcurrency:
    def test_put_without_if_match_returns_412(self, admin_client, verified_source):
        obj = _create(admin_client, verified_source["id"])
        r = admin_client.put(f"/admin/demo_indicator/{obj['id']}", json={"name": "x"})
        assert r.status_code == 412

    def test_put_wrong_if_match_returns_412(self, admin_client, verified_source):
        obj = _create(admin_client, verified_source["id"])
        r = admin_client.put(
            f"/admin/demo_indicator/{obj['id']}",
            headers={"If-Match": '"v999"'},
            json={"name": "x"},
        )
        assert r.status_code == 412

    def test_put_correct_if_match_returns_200(self, admin_client, verified_source):
        obj = _create(admin_client, verified_source["id"])
        r = admin_client.put(
            f"/admin/demo_indicator/{obj['id']}",
            headers={"If-Match": '"v1"'},
            json={"name": "Updated name"},
        )
        assert r.status_code == 200, r.text
        assert r.json()["name"] == "Updated name"

    def test_put_published_creates_new_version(self, admin_client, verified_source):
        obj = _create(admin_client, verified_source["id"])
        # Publish
        r = admin_client.post(
            f"/admin/demo_indicator/{obj['id']}/publish",
            headers={"If-Match": '"v1"'},
        )
        assert r.status_code == 200
        # Edit published → new version
        r2 = admin_client.put(
            f"/admin/demo_indicator/{obj['id']}",
            headers={"If-Match": '"v1"'},
            json={"name": "v2 name"},
        )
        assert r2.status_code == 200, r2.text
        new_obj = r2.json()
        assert new_obj["version"] == 2
        assert new_obj["status"] == "draft"
        assert r2.headers.get("ETag") == '"v2"'
        # Old object should now be 'outdated'
        r3 = admin_client.get(f"/admin/demo_indicator/{obj['id']}")
        assert r3.status_code == 200
        assert r3.json()["status"] == "outdated"
        # Versions endpoint returns at least 2 entries
        r4 = admin_client.get(f"/admin/demo_indicator/{new_obj['id']}/versions")
        assert r4.status_code == 200
        items = r4.json()["items"]
        assert len(items) >= 2
