"""F09 T082 — Validateur publish Référentiel (FR-005, SC-004)."""

from __future__ import annotations

import time
import uuid

from tests.integration.conftest import requires_db


def _uniq(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4].upper()}"


def _ind_payload(code: str, source_ids: list[str]) -> dict:
    return {
        "code": code,
        "name": "I",
        "definition": "x",
        "pillar": "E",
        "unite": "kg",
        "value_type": "numeric",
        "source_ids": source_ids,
    }


def _ref_payload(code: str, source_ids: list[str]) -> dict:
    return {
        "code": code,
        "name": "R",
        "publisher": "M",
        "type": "transverse",
        "formula_type": "weighted_sum",
        "source_ids": source_ids,
    }


@requires_db
class TestPublishValidator:
    def test_no_indicateurs_publish_409(self, admin_client, verified_source):
        ref = admin_client.post(
            "/admin/referentiels/",
            json=_ref_payload(_uniq("VAL_NOI"), [verified_source["id"]]),
        ).json()
        r = admin_client.post(
            f"/admin/referentiels/{ref['id']}/publish", headers={"If-Match": '"v1"'}
        )
        assert r.status_code == 409
        codes = [f["code"] for f in r.json()["detail"]["failures"]]
        assert "no_indicateurs" in codes

    def test_weights_sum_invalid(self, admin_client, verified_source):
        ind = admin_client.post(
            "/admin/indicateurs/",
            json=_ind_payload(_uniq("VAL_W"), [verified_source["id"]]),
        ).json()
        admin_client.post(
            f"/admin/indicateurs/{ind['id']}/publish", headers={"If-Match": '"v1"'}
        )
        ref = admin_client.post(
            "/admin/referentiels/",
            json=_ref_payload(_uniq("VAL_W"), [verified_source["id"]]),
        ).json()
        admin_client.post(
            f"/admin/referentiels/{ref['id']}/indicateurs",
            json={
                "indicateur_id": ind["id"],
                "poids": "50",  # < 100
                "source_id": verified_source["id"],
            },
        )
        r = admin_client.post(
            f"/admin/referentiels/{ref['id']}/publish", headers={"If-Match": '"v1"'}
        )
        assert r.status_code == 409
        codes = [f["code"] for f in r.json()["detail"]["failures"]]
        assert "weights_sum_invalid" in codes

    def test_indicateur_not_published_blocks(self, admin_client, verified_source):
        ind = admin_client.post(
            "/admin/indicateurs/",
            json=_ind_payload(_uniq("VAL_INP"), [verified_source["id"]]),
        ).json()  # leave as draft
        ref = admin_client.post(
            "/admin/referentiels/",
            json=_ref_payload(_uniq("VAL_INP"), [verified_source["id"]]),
        ).json()
        admin_client.post(
            f"/admin/referentiels/{ref['id']}/indicateurs",
            json={
                "indicateur_id": ind["id"],
                "poids": "100",
                "source_id": verified_source["id"],
            },
        )
        r = admin_client.post(
            f"/admin/referentiels/{ref['id']}/publish", headers={"If-Match": '"v1"'}
        )
        assert r.status_code == 409
        codes = [f["code"] for f in r.json()["detail"]["failures"]]
        assert "indicateurs_not_published" in codes

    def test_full_valid_publishes(self, admin_client, verified_source):
        ind = admin_client.post(
            "/admin/indicateurs/",
            json=_ind_payload(_uniq("VAL_OK"), [verified_source["id"]]),
        ).json()
        admin_client.post(
            f"/admin/indicateurs/{ind['id']}/publish", headers={"If-Match": '"v1"'}
        )
        ref = admin_client.post(
            "/admin/referentiels/",
            json=_ref_payload(_uniq("VAL_OK"), [verified_source["id"]]),
        ).json()
        admin_client.post(
            f"/admin/referentiels/{ref['id']}/indicateurs",
            json={
                "indicateur_id": ind["id"],
                "poids": "100",
                "source_id": verified_source["id"],
            },
        )
        r = admin_client.post(
            f"/admin/referentiels/{ref['id']}/publish", headers={"If-Match": '"v1"'}
        )
        assert r.status_code == 200, r.text
        assert r.json()["status"] == "published"
