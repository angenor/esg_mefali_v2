"""F06 P2 — search + stats integration tests."""

from __future__ import annotations

from tests.integration.conftest import requires_db


@requires_db
class TestSearchAndStats:
    def test_search_q_too_short_returns_422(self, admin_client):
        # FastAPI's Query(min_length=2) yields 422.
        r = admin_client.get("/admin/search?q=a")
        assert r.status_code == 422

    def test_search_returns_grouped_results(self, admin_client, verified_source):
        admin_client.post(
            "/admin/demo_indicator/",
            json={
                "name": "Searchable Indicator Foo",
                "publisher": "Pub-Foo",
                "external_id": f"SR-{verified_source['id'][:8]}",
                "source_id": verified_source["id"],
            },
        )
        r = admin_client.get("/admin/search?q=Searchable")
        assert r.status_code == 200, r.text
        body = r.json()
        assert body["query"] == "Searchable"
        assert any(g["entity"] == "demo_indicator" for g in body["groups"])
        items = next(g["items"] for g in body["groups"] if g["entity"] == "demo_indicator")
        assert len(items) >= 1
        assert any("Searchable" in (it.get("name") or "") for it in items)

    def test_stats_returns_counters(self, admin_client, verified_source):
        admin_client.post(
            "/admin/demo_indicator/",
            json={
                "name": "Stats Test",
                "external_id": f"ST-{verified_source['id'][:8]}",
                "source_id": verified_source["id"],
            },
        )
        r = admin_client.get("/admin/stats/catalog")
        assert r.status_code == 200, r.text
        body = r.json()
        assert "demo_indicator" in body
        counters = body["demo_indicator"]
        for key in ("draft", "published", "outdated", "pending"):
            assert key in counters
            assert isinstance(counters[key], int)
        assert counters["draft"] >= 1
