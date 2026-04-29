"""F09 T014 — Tests CRUD ``indicateur`` (admin)."""

from __future__ import annotations

import time
import uuid

from tests.integration.conftest import requires_db


def _uniq(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4].upper()}"


def _payload(code: str, *, pillar: str = "E", value_type: str = "numeric") -> dict:
    return {
        "code": code,
        "name": "GHG Scope 1",
        "definition": "Émissions directes",
        "pillar": pillar,
        "unite": "tCO2e",
        "value_type": value_type,
    }


@requires_db
class TestIndicateurCRUD:
    def test_create_returns_201_with_etag(self, admin_client):
        r = admin_client.post("/admin/indicateurs/", json=_payload(_uniq("CREATE")))
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["status"] == "draft"
        assert r.headers.get("ETag") == '"v1"'

    def test_code_normalized_uppercase(self, admin_client):
        code = _uniq("LOWER").lower()
        r = admin_client.post("/admin/indicateurs/", json=_payload(code))
        assert r.status_code == 201
        assert r.json()["code"] == code.upper()

    def test_invalid_code_format_rejected(self, admin_client):
        r = admin_client.post("/admin/indicateurs/", json=_payload("123-bad"))
        assert r.status_code == 422

    def test_enum_values_required(self, admin_client):
        body = _payload(_uniq("ENUM"), value_type="enum")
        r = admin_client.post("/admin/indicateurs/", json=body)
        assert r.status_code == 422

    def test_list_filter_pillar(self, admin_client):
        e_code = _uniq("LISTE")
        s_code = _uniq("LISTS")
        admin_client.post("/admin/indicateurs/", json=_payload(e_code, pillar="E"))
        admin_client.post("/admin/indicateurs/", json=_payload(s_code, pillar="S"))
        r = admin_client.get("/admin/indicateurs/?pillar=S")
        assert r.status_code == 200
        codes = [i["code"] for i in r.json()["items"]]
        assert s_code in codes
        assert e_code not in codes

    def test_patch_in_draft(self, admin_client):
        r = admin_client.post("/admin/indicateurs/", json=_payload(_uniq("PATCH")))
        obj = r.json()
        r2 = admin_client.patch(
            f"/admin/indicateurs/{obj['id']}",
            json={"name": "Renamed"},
            headers={"If-Match": '"v1"'},
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["name"] == "Renamed"
        assert r2.headers["ETag"] == '"v1"'

    def test_get_by_id(self, admin_client):
        code = _uniq("GET")
        r = admin_client.post("/admin/indicateurs/", json=_payload(code))
        obj = r.json()
        r2 = admin_client.get(f"/admin/indicateurs/{obj['id']}")
        assert r2.status_code == 200
        assert r2.json()["code"] == code

    def test_etag_mismatch_412(self, admin_client):
        r = admin_client.post("/admin/indicateurs/", json=_payload(_uniq("ETAG")))
        obj = r.json()
        r2 = admin_client.patch(
            f"/admin/indicateurs/{obj['id']}",
            json={"name": "X"},
            headers={"If-Match": '"v9"'},
        )
        assert r2.status_code == 412
