"""F08 US4 — tests Offre CRUD + accreditation gate + /effective + unique constraint."""

from __future__ import annotations

from datetime import date, timedelta
from uuid import uuid4

from tests.integration.conftest import requires_db


def _fonds(client, sid: str, name: str) -> str:
    body = {
        "name": name,
        "organisation": "Org",
        "type": "multilateral",
        "submission_mode": "rolling",
        "criteres_json": [
            {"key": "max_amount", "operator": "max", "value": 10_000_000,
             "unit": None, "source_id": sid},
        ],
        "documents_requis_json": [],
        "frais_json": {"origination_pct": 1.0, "currency": "EUR"},
        "delais_json": {"instruction_jours": 30},
        "thematique": ["climat"],
        "instruments": ["don"],
        "eligibilite_geo": ["CI"],
        "source_ids": [sid],
    }
    r = client.post("/admin/fonds/", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _inter(client, sid: str, name: str) -> str:
    body = {
        "name": name,
        "type": "banque_locale",
        "pays": ["CI"],
        "criteres_json": [
            {"key": "max_amount", "operator": "max", "value": 5_000_000,
             "unit": None, "source_id": sid},
        ],
        "documents_requis_json": [],
        "frais_json": {"marge_pct": 0.5, "currency": "EUR"},
        "delais_json": {"decaissement_jours": 60},
        "source_ids": [sid],
    }
    r = client.post("/admin/intermediaires/", json=body)
    assert r.status_code == 201, r.text
    return r.json()["id"]


def _accreditation(client, fid: str, iid: str, sid: str) -> str:
    r = client.post(
        "/admin/accreditations/",
        json={
            "intermediaire_id": iid,
            "fonds_id": fid,
            "valid_from": (date.today() - timedelta(days=30)).isoformat(),
            "valid_to": (date.today() + timedelta(days=365)).isoformat(),
            "source_id": sid,
        },
    )
    assert r.status_code == 201, r.text
    return r.json()["id"]


@requires_db
class TestOffreAdmin:
    def test_create_offre_requires_active_accreditation(self, admin_client, verified_source):
        sid = verified_source["id"]
        fid = _fonds(admin_client, sid, f"F-acc-{uuid4().hex[:6]}")
        iid = _inter(admin_client, sid, f"I-acc-{uuid4().hex[:6]}")
        # No accreditation → 409
        r = admin_client.post(
            "/admin/offres/",
            json={
                "fonds_id": fid, "intermediaire_id": iid,
                "name": "Offre KO", "source_ids": [sid],
            },
        )
        assert r.status_code == 409
        # With accreditation → 201
        _accreditation(admin_client, fid, iid, sid)
        r2 = admin_client.post(
            "/admin/offres/",
            json={
                "fonds_id": fid, "intermediaire_id": iid,
                "name": "Offre OK", "source_ids": [sid],
            },
        )
        assert r2.status_code == 201, r2.text

    def test_unique_constraint_fonds_inter_name(self, admin_client, verified_source):
        sid = verified_source["id"]
        fid = _fonds(admin_client, sid, f"F-uq-{uuid4().hex[:6]}")
        iid = _inter(admin_client, sid, f"I-uq-{uuid4().hex[:6]}")
        _accreditation(admin_client, fid, iid, sid)
        body = {
            "fonds_id": fid, "intermediaire_id": iid,
            "name": "Offre dup", "source_ids": [sid],
        }
        r = admin_client.post("/admin/offres/", json=body)
        assert r.status_code == 201
        r2 = admin_client.post("/admin/offres/", json=body)
        assert r2.status_code in (409, 422)

    def test_get_effective_returns_two_layer_tree(self, admin_client, verified_source):
        sid = verified_source["id"]
        fid = _fonds(admin_client, sid, f"F-eff-{uuid4().hex[:6]}")
        iid = _inter(admin_client, sid, f"I-eff-{uuid4().hex[:6]}")
        _accreditation(admin_client, fid, iid, sid)
        r = admin_client.post(
            "/admin/offres/",
            json={
                "fonds_id": fid, "intermediaire_id": iid,
                "name": "Offre eff", "source_ids": [sid],
            },
        )
        oid = r.json()["id"]
        r2 = admin_client.get(f"/admin/offres/{oid}/effective")
        assert r2.status_code == 200, r2.text
        eff = r2.json()
        assert "fonds_layer" in eff
        assert "intermediaire_layer" in eff
        assert "criteres_effectifs" in eff
        assert "snapshot_hash" in eff
        # max_amount fusion: min(10M, 5M) = 5M
        crit = next(c for c in eff["criteres_effectifs"] if c["key"] == "max_amount")
        assert crit["value"] == 5_000_000
        # delais sum: 30 + 60 = 90
        assert eff["delais_effectifs_jours"] == 90

    def test_publish_gate_offre(self, admin_client, verified_source):
        sid = verified_source["id"]
        fid = _fonds(admin_client, sid, f"F-pub-{uuid4().hex[:6]}")
        iid = _inter(admin_client, sid, f"I-pub-{uuid4().hex[:6]}")
        _accreditation(admin_client, fid, iid, sid)
        r = admin_client.post(
            "/admin/offres/",
            json={
                "fonds_id": fid, "intermediaire_id": iid,
                "name": "Offre pub", "source_ids": [sid],
            },
        )
        oid = r.json()["id"]
        r2 = admin_client.post(
            f"/admin/offres/{oid}/publish", headers={"If-Match": '"v1"'}
        )
        assert r2.status_code == 200, r2.text
        assert r2.json()["status"] == "published"
