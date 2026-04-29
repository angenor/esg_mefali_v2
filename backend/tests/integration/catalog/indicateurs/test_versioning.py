"""F09 T016 — versioning : modifier published → v2 draft."""

from __future__ import annotations

import time
import uuid

from tests.integration.conftest import requires_db


def _uniq(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{uuid.uuid4().hex[:4].upper()}"


def _payload(code: str, source_ids: list[str]) -> dict:
    return {
        "code": code,
        "name": "Vers",
        "definition": "x",
        "pillar": "E",
        "unite": "kg",
        "value_type": "numeric",
        "source_ids": source_ids,
    }


@requires_db
def test_modify_published_creates_new_version(admin_client, verified_source):
    r = admin_client.post(
        "/admin/indicateurs/", json=_payload(_uniq("VER"), [verified_source["id"]])
    )
    obj = r.json()
    r2 = admin_client.post(
        f"/admin/indicateurs/{obj['id']}/publish", headers={"If-Match": '"v1"'}
    )
    assert r2.status_code == 200
    pub = r2.json()
    r3 = admin_client.patch(
        f"/admin/indicateurs/{pub['id']}",
        json={"name": "Renamed v2"},
        headers={"If-Match": '"v1"'},
    )
    assert r3.status_code == 200, r3.text
    new_obj = r3.json()
    assert new_obj["status"] == "draft"
    assert new_obj["version"] == 2
    assert new_obj["name"] == "Renamed v2"
    assert verified_source["id"] in [str(s) for s in new_obj["source_ids"]]
