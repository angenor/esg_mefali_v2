"""F09 T046 — Filtre owner_type/owner_id critères + tri par severity (FR-009)."""

from __future__ import annotations

import uuid

from tests.integration.conftest import requires_db


def _critere(owner_id: str, severity: str, source_id: str) -> dict:
    return {
        "owner_type": "fonds",
        "owner_id": owner_id,
        "label": f"crit-{severity}",
        "severity": severity,
        "expression_json": {"const": True},
        "source_id": source_id,
    }


@requires_db
def test_filter_by_owner_sorted_by_severity(admin_client, verified_source):
    owner_id = str(uuid.uuid4())
    other_id = str(uuid.uuid4())
    # Create 3 critères for the same owner with different severities
    for sev in ("info", "blocking", "warning"):
        admin_client.post(
            "/admin/criteres/", json=_critere(owner_id, sev, verified_source["id"])
        )
    # And 1 critère for a different owner.
    admin_client.post(
        "/admin/criteres/", json=_critere(other_id, "blocking", verified_source["id"])
    )
    r = admin_client.get(
        f"/admin/criteres/?owner_type=fonds&owner_id={owner_id}"
    )
    assert r.status_code == 200
    items = r.json()["items"]
    # Filtered to 3 items, all with same owner.
    assert len(items) == 3
    assert all(i["owner_id"] == owner_id for i in items)
    # Sorted blocking → warning → info.
    severities = [i["severity"] for i in items]
    assert severities == ["blocking", "warning", "info"]


@requires_db
def test_dsl_invalid_rejected(admin_client, verified_source):
    payload = {
        "owner_type": "fonds",
        "owner_id": str(uuid.uuid4()),
        "label": "bad",
        "severity": "warning",
        "expression_json": {"exec": ["rm"]},
        "source_id": verified_source["id"],
    }
    r = admin_client.post("/admin/criteres/", json=payload)
    assert r.status_code == 422


@requires_db
def test_evaluate_endpoint(admin_client, verified_source):
    expr = {"gt": [{"var": "score"}, {"const": 50}]}
    payload = {
        "owner_type": "fonds",
        "owner_id": str(uuid.uuid4()),
        "label": "score>50",
        "severity": "info",
        "expression_json": expr,
        "source_id": verified_source["id"],
    }
    r = admin_client.post("/admin/criteres/", json=payload)
    obj = r.json()
    e1 = admin_client.post(
        f"/admin/criteres/{obj['id']}/evaluate", json={"score": 70}
    )
    assert e1.status_code == 200
    assert e1.json()["result"] is True
    e2 = admin_client.post(
        f"/admin/criteres/{obj['id']}/evaluate", json={"score": 30}
    )
    assert e2.json()["result"] is False
    e3 = admin_client.post(f"/admin/criteres/{obj['id']}/evaluate", json={})
    assert e3.json()["result"] is None
