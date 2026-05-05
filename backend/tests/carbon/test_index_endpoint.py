"""F47 T009 — Tests carbon list_index (GET /me/carbon)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from uuid import uuid4

from app.carbon import service as carbon_service
from tests.carbon._fakes import FakeSession


class TestListIndex:
    def test_no_footprint_returns_empty(self):
        db = FakeSession(index_rows=[])
        result = carbon_service.list_index(db, account_id=uuid4())
        assert result == []
        assert any(
            "SELECT DISTINCT ON (year)" in s for s, _ in db.executed
        )

    def test_three_years_descending(self):
        rows = [
            {
                "id": uuid4(),
                "year": 2026,
                "total_tco2e": "12.4",
                "computed_at": datetime(2026, 5, 1, tzinfo=UTC),
                "version": 1,
            },
            {
                "id": uuid4(),
                "year": 2025,
                "total_tco2e": "13.8",
                "computed_at": datetime(2025, 12, 15, tzinfo=UTC),
                "version": 2,
            },
            {
                "id": uuid4(),
                "year": 2024,
                "total_tco2e": "15.2",
                "computed_at": datetime(2024, 11, 1, tzinfo=UTC),
                "version": 1,
            },
        ]
        db = FakeSession(index_rows=rows)
        result = carbon_service.list_index(db, account_id=uuid4())
        assert len(result) == 3
        assert [r["year"] for r in result] == [2026, 2025, 2024]
        assert result[1]["version"] == 2
        assert isinstance(result[0]["total_tco2e"], Decimal)

    def test_distinct_on_year_via_sql(self):
        """Doit emettre 'DISTINCT ON (year)' dans le SQL pour ne garder
        qu'une empreinte par annee (la plus recente)."""
        db = FakeSession(index_rows=[])
        carbon_service.list_index(db, account_id=uuid4())
        sql = db.executed[0][0]
        assert "DISTINCT ON (year)" in sql
        assert "ORDER BY year DESC" in sql

    def test_limit_years_param_passed(self):
        db = FakeSession(index_rows=[])
        carbon_service.list_index(db, account_id=uuid4(), limit_years=2)
        params = db.executed[0][1]
        assert params["limit"] == 2

    def test_account_id_param_passed(self):
        aid = uuid4()
        db = FakeSession(index_rows=[])
        carbon_service.list_index(db, account_id=aid)
        params = db.executed[0][1]
        assert params["aid"] == str(aid)
