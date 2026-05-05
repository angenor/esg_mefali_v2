"""F47 T017 — Tests carbon edit_line (POST /me/carbon/{year}/edit-line)."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest

from app.carbon import service as carbon_service
from app.carbon.schemas import CarbonEditLineRequest
from tests.carbon._fakes import FakeSession, fake_full_row, make_factor_lookup


@pytest.fixture()
def patch_factor(monkeypatch):
    fid, sid, fn = make_factor_lookup(scope="2", categorie="electricite")
    monkeypatch.setattr(
        "app.catalog.facteurs_emission.lookup.get_facteur", fn
    )
    return fid, sid


def _payload(code="electricite", quantity="45000", source_id=None):
    return CarbonEditLineRequest(
        code=code,
        quantity=Decimal(quantity),
        country="CI",
        source_id=source_id or uuid4(),
    )


class TestEditLine:
    def test_source_not_verified_raises(self, patch_factor):
        # Pas de source_row → SELECT statut FROM source retourne NoneResult
        db = FakeSession(source_row=None)
        with pytest.raises(carbon_service.SourceNotVerified):
            carbon_service.edit_line(
                db,
                account_id=uuid4(),
                year=2026,
                user_id=None,
                payload=_payload(),
            )

    def test_source_pending_raises(self, patch_factor):
        db = FakeSession(source_row={"statut": "pending"})
        with pytest.raises(carbon_service.SourceNotVerified):
            carbon_service.edit_line(
                db,
                account_id=uuid4(),
                year=2026,
                user_id=None,
                payload=_payload(),
            )

    def test_no_footprint_raises(self, patch_factor):
        db = FakeSession(
            source_row={"statut": "verified"},
            select_full_row=None,
        )
        with pytest.raises(carbon_service.FootprintNotFound):
            carbon_service.edit_line(
                db,
                account_id=uuid4(),
                year=2026,
                user_id=None,
                payload=_payload(),
            )

    def test_existing_line_replaced(self, patch_factor):
        original_source = uuid4()
        db = FakeSession(
            source_row={"statut": "verified"},
            select_full_row=fake_full_row(
                items=[
                    {
                        "code": "electricite",
                        "quantity": "50000",
                        "country": "CI",
                        "source_id": str(original_source),
                    }
                ],
                version=1,
            ),
        )
        result = carbon_service.edit_line(
            db,
            account_id=uuid4(),
            year=2026,
            user_id=None,
            payload=_payload(quantity="45000"),
        )
        assert result["edited_line_code"] == "electricite"
        assert result["version"] == 2
        # Le breakdown doit refléter la nouvelle quantité (45000 * 0.5 / 1000 = 22.5 tCO2e)
        assert any(
            ln["quantity"] == "45000" for ln in result["breakdown"]
        )

    def test_new_line_appended(self, patch_factor):
        db = FakeSession(
            source_row={"statut": "verified"},
            select_full_row=fake_full_row(
                items=[
                    {
                        "code": "deplacements",
                        "quantity": "8000",
                        "country": None,
                        "source_id": str(uuid4()),
                    }
                ],
                version=1,
            ),
        )
        result = carbon_service.edit_line(
            db,
            account_id=uuid4(),
            year=2026,
            user_id=None,
            payload=_payload(code="electricite", quantity="50000"),
        )
        assert len(result["breakdown"]) == 2
        codes = {ln["code"] for ln in result["breakdown"]}
        assert codes == {"deplacements", "electricite"}

    def test_factor_missing_raises(self, monkeypatch):
        monkeypatch.setattr(
            "app.catalog.facteurs_emission.lookup.get_facteur",
            lambda *a, **k: None,
        )
        db = FakeSession(
            source_row={"statut": "verified"},
            select_full_row=fake_full_row(
                items=[
                    {
                        "code": "electricite",
                        "quantity": "50000",
                        "country": "CI",
                        "source_id": str(uuid4()),
                    }
                ],
                version=1,
            ),
        )
        with pytest.raises(carbon_service.FactorNotFound):
            carbon_service.edit_line(
                db,
                account_id=uuid4(),
                year=2026,
                user_id=None,
                payload=_payload(),
            )

    def test_audit_emitted_on_success(self, patch_factor):
        db = FakeSession(
            source_row={"statut": "verified"},
            select_full_row=fake_full_row(
                items=[
                    {
                        "code": "electricite",
                        "quantity": "50000",
                        "country": "CI",
                        "source_id": str(uuid4()),
                    }
                ],
                version=1,
            ),
        )
        carbon_service.edit_line(
            db,
            account_id=uuid4(),
            year=2026,
            user_id=None,
            payload=_payload(quantity="45000"),
        )
        sqls = [s for s, _ in db.executed]
        # 2 INSERT carbon_footprint (1 par compute_footprint), 2 INSERT audit_log
        # (1 pour compute, 1 pour edit-line)
        assert sum(1 for s in sqls if "INSERT INTO carbon_footprint" in s) == 1
        assert sum(1 for s in sqls if "INSERT INTO audit_log" in s) == 2
