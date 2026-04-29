"""F09 T034 — CRUD ``referentiel``."""

from __future__ import annotations

import time
import uuid

from tests.integration.conftest import requires_db


def _uniq(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4].upper()}"


def _payload(code: str, source_ids: list[str] | None = None) -> dict:
    return {
        "code": code,
        "name": "Référentiel test",
        "publisher": "Mefali",
        "type": "transverse",
        "formula_type": "weighted_sum",
        "source_ids": source_ids or [],
    }


@requires_db
class TestReferentielCRUD:
    def test_create_returns_201_with_etag(self, admin_client):
        r = admin_client.post("/admin/referentiels/", json=_payload(_uniq("REF")))
        assert r.status_code == 201, r.text
        assert r.headers.get("ETag") == '"v1"'

    def test_get_full_returns_indicateurs_and_sources(
        self, admin_client, verified_source
    ):
        # Create indicateur + referentiel + attach.
        ind = admin_client.post(
            "/admin/indicateurs/",
            json={
                "code": _uniq("IFULL"),
                "name": "I",
                "definition": "x",
                "pillar": "E",
                "unite": "kg",
                "value_type": "numeric",
                "source_ids": [verified_source["id"]],
            },
        ).json()
        ref = admin_client.post(
            "/admin/referentiels/",
            json=_payload(_uniq("RFULL"), [verified_source["id"]]),
        ).json()
        att = admin_client.post(
            f"/admin/referentiels/{ref['id']}/indicateurs",
            json={
                "indicateur_id": ind["id"],
                "poids": "100",
                "source_id": verified_source["id"],
            },
        )
        assert att.status_code == 200, att.text
        full = admin_client.get(f"/admin/referentiels/{ref['id']}/full").json()
        assert any(i["code"] == ind["code"] for i in full["indicateurs"])
        assert any(s["id"] == verified_source["id"] for s in full["sources"])

    def test_attach_then_detach_indicateur(self, admin_client, verified_source):
        ind = admin_client.post(
            "/admin/indicateurs/",
            json={
                "code": _uniq("IDET"),
                "name": "I",
                "definition": "x",
                "pillar": "E",
                "unite": "kg",
                "value_type": "numeric",
                "source_ids": [verified_source["id"]],
            },
        ).json()
        ref = admin_client.post(
            "/admin/referentiels/",
            json=_payload(_uniq("RDET"), [verified_source["id"]]),
        ).json()
        admin_client.post(
            f"/admin/referentiels/{ref['id']}/indicateurs",
            json={
                "indicateur_id": ind["id"],
                "poids": "50",
                "source_id": verified_source["id"],
            },
        )
        d = admin_client.delete(
            f"/admin/referentiels/{ref['id']}/indicateurs/{ind['id']}"
        )
        assert d.status_code == 204
        full = admin_client.get(f"/admin/referentiels/{ref['id']}/full").json()
        assert all(i["code"] != ind["code"] for i in full["indicateurs"])
