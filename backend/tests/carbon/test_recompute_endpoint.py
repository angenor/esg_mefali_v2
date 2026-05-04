"""F47 T013 — Tests carbon recompute (POST /me/carbon/{year}/recompute)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.carbon import service as carbon_service
from tests.carbon._fakes import FakeSession, fake_full_row, make_factor_lookup


@pytest.fixture()
def patch_factor(monkeypatch):
    fid, sid, fn = make_factor_lookup(scope="2", categorie="electricite")
    monkeypatch.setattr(
        "app.catalog.facteurs_emission.lookup.get_facteur", fn
    )
    return fid, sid


class TestRecompute:
    def test_year_without_footprint_raises(self):
        db = FakeSession(select_full_row=None)
        with pytest.raises(carbon_service.FootprintNotFound):
            carbon_service.recompute(
                db, account_id=uuid4(), year=2026, user_id=None
            )

    def test_recompute_creates_new_footprint_with_incremented_version(
        self, patch_factor
    ):
        prev_id = uuid4()
        db = FakeSession(
            select_full_row=fake_full_row(
                items=[
                    {
                        "code": "ELEC_CIV",
                        "quantity": "100",
                        "country": "CI",
                        "source_id": str(uuid4()),
                    }
                ],
                version=2,
                fp_id=prev_id,
            )
        )
        result = carbon_service.recompute(
            db, account_id=uuid4(), year=2026, user_id=None
        )
        assert result["previous_footprint_id"] == prev_id
        assert result["version"] == 3
        # Au moins un INSERT carbon_footprint et un INSERT audit_log
        sqls = [s for s, _ in db.executed]
        assert any("INSERT INTO carbon_footprint" in s for s in sqls)
        # Le SELECT _load_latest_full a bien été émis
        assert any("computed_at, version, source_data_json" in s for s in sqls)

    def test_recompute_uses_previous_source_data(self, patch_factor):
        items = [
            {"code": "ELEC_CIV", "quantity": "100", "country": "CI", "source_id": str(uuid4())},
            {"code": "DIESEL", "quantity": "50", "country": None, "source_id": str(uuid4())},
        ]
        db = FakeSession(select_full_row=fake_full_row(items=items, version=1))
        result = carbon_service.recompute(
            db, account_id=uuid4(), year=2026, user_id=None
        )
        # 2 lignes calculées (et donc dans breakdown)
        assert len(result["breakdown"]) == 2

    def test_empty_source_data_raises(self):
        db = FakeSession(select_full_row=fake_full_row(items=[], version=1))
        with pytest.raises(carbon_service.FootprintNotFound):
            carbon_service.recompute(
                db, account_id=uuid4(), year=2026, user_id=None
            )

    def test_factor_missing_propagates(self, monkeypatch):
        monkeypatch.setattr(
            "app.catalog.facteurs_emission.lookup.get_facteur",
            lambda *a, **k: None,
        )
        db = FakeSession(
            select_full_row=fake_full_row(
                items=[{"code": "UNKNOWN", "quantity": "1", "country": None, "source_id": None}],
                version=1,
            )
        )
        with pytest.raises(carbon_service.FactorNotFound):
            carbon_service.recompute(
                db, account_id=uuid4(), year=2026, user_id=None
            )
