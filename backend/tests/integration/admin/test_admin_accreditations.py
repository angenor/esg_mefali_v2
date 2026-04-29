"""F08 US3 — tests Accréditation CRUD + helper is_active + offre gate."""

from __future__ import annotations

from datetime import date, timedelta

import pytest

from tests.integration.conftest import requires_db


def _fonds_payload(source_id: str, *, name: str = "GCF-acc") -> dict:
    return {
        "name": name,
        "organisation": "GCF",
        "type": "multilateral",
        "submission_mode": "rolling",
        "criteres_json": [],
        "documents_requis_json": [],
        "frais_json": {},
        "delais_json": {},
        "thematique": [],
        "instruments": [],
        "eligibilite_geo": ["CI"],
        "source_ids": [source_id],
    }


def _inter_payload(source_id: str, *, name: str = "BOAD-acc") -> dict:
    return {
        "name": name,
        "type": "banque_locale",
        "pays": ["CI"],
        "criteres_json": [],
        "documents_requis_json": [],
        "frais_json": {},
        "delais_json": {},
        "source_ids": [source_id],
    }


def _setup_pair(client, sid: str, name_suffix: str) -> tuple[str, str]:
    f = client.post("/admin/fonds/", json=_fonds_payload(sid, name=f"Fonds-{name_suffix}")).json()
    i = client.post("/admin/intermediaires/", json=_inter_payload(sid, name=f"Inter-{name_suffix}")).json()
    return f["id"], i["id"]


@requires_db
class TestAccreditation:
    def test_create_with_source_and_money(self, admin_client, verified_source):
        fid, iid = _setup_pair(admin_client, verified_source["id"], "create")
        body = {
            "intermediaire_id": iid,
            "fonds_id": fid,
            "valid_from": date.today().isoformat(),
            "valid_to": (date.today() + timedelta(days=365)).isoformat(),
            "plafond_money": {"amount": 10_000_000, "currency": "USD"},
            "source_id": verified_source["id"],
            "notes": "Accréditation test",
        }
        r = admin_client.post("/admin/accreditations/", json=body)
        assert r.status_code == 201, r.text
        assert r.json()["plafond_money"]["amount"] == 10_000_000

    @pytest.mark.parametrize(
        "vf_offset,vt_offset,expected",
        [
            (-30, 30, True),    # active range
            (-30, None, True),  # open-ended
            (-365, -30, False), # expired
            (30, 60, False),    # future
        ],
    )
    def test_is_active_helper(self, admin_client, verified_source, vf_offset, vt_offset, expected):
        fid, iid = _setup_pair(
            admin_client, verified_source["id"], f"isactive-{vf_offset}-{vt_offset}"
        )
        vt = (
            (date.today() + timedelta(days=vt_offset)).isoformat()
            if vt_offset is not None else None
        )
        r = admin_client.post(
            "/admin/accreditations/",
            json={
                "intermediaire_id": iid,
                "fonds_id": fid,
                "valid_from": (date.today() + timedelta(days=vf_offset)).isoformat(),
                "valid_to": vt,
                "source_id": verified_source["id"],
            },
        )
        assert r.status_code == 201
        acc_id = r.json()["id"]
        r2 = admin_client.get(f"/admin/accreditations/{acc_id}/is_active")
        assert r2.status_code == 200
        assert r2.json()["active"] is expected

    def test_offre_creation_refused_without_active_accreditation(
        self, admin_client, verified_source
    ):
        fid, iid = _setup_pair(admin_client, verified_source["id"], "no-acc")
        # NO accreditation created → POST offre should 409.
        r = admin_client.post(
            "/admin/offres/",
            json={
                "fonds_id": fid,
                "intermediaire_id": iid,
                "name": "Offre invalide",
                "accepted_languages": ["fr"],
                "criteres_offre_specifiques": [],
                "documents_specifiques": [],
                "frais_specifiques": {},
                "delais_specifiques": {},
                "source_ids": [verified_source["id"]],
            },
        )
        assert r.status_code == 409, r.text
        assert r.json()["detail"]["code"] == "no_active_accreditation"
