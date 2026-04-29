"""F09 T051 — CRUD ``document_requis`` + filtre owner."""

from __future__ import annotations

import uuid

from tests.integration.conftest import requires_db


def _payload(owner_id: str, source_id: str, name: str) -> dict:
    return {
        "owner_type": "fonds",
        "owner_id": owner_id,
        "name": name,
        "type": "juridique",
        "source_id": source_id,
    }


@requires_db
class TestDocumentRequisCRUD:
    def test_create_returns_201(self, admin_client, verified_source):
        owner = str(uuid.uuid4())
        r = admin_client.post(
            "/admin/documents-requis/",
            json=_payload(owner, verified_source["id"], "KYC"),
        )
        assert r.status_code == 201, r.text
        assert r.json()["name"] == "KYC"

    def test_filter_by_owner(self, admin_client, verified_source):
        owner_a = str(uuid.uuid4())
        owner_b = str(uuid.uuid4())
        admin_client.post(
            "/admin/documents-requis/",
            json=_payload(owner_a, verified_source["id"], "DOC_A"),
        )
        admin_client.post(
            "/admin/documents-requis/",
            json=_payload(owner_b, verified_source["id"], "DOC_B"),
        )
        r = admin_client.get(
            f"/admin/documents-requis/?owner_type=fonds&owner_id={owner_a}"
        )
        names = [i["name"] for i in r.json()["items"]]
        assert "DOC_A" in names
        assert "DOC_B" not in names

    def test_required_when_dsl_validated(self, admin_client, verified_source):
        body = _payload(str(uuid.uuid4()), verified_source["id"], "C")
        body["required_when"] = {"exec": "rm"}  # invalid op
        r = admin_client.post("/admin/documents-requis/", json=body)
        assert r.status_code == 422
