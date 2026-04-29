"""F29 - Tests unitaires parser CSV Mobile Money."""

from __future__ import annotations

import pytest

from app.credit.csv_parser import (
    MAX_BYTES,
    MAX_ROWS,
    StatementParseError,
    StatementTooLargeError,
    parse_statement,
)


def _csv(rows: list[str]) -> bytes:
    header = "date_iso,amount_xof,direction,counterparty\n"
    return (header + "\n".join(rows) + "\n").encode("utf-8")


def test_parse_nominal_two_months():
    raw = _csv(
        [
            "2026-04-01,150000,in,client_a",
            "2026-04-15,80000,out,fournisseur_x",
            "2026-05-02,200000,in,client_b",
            "2026-05-20,50000,out,",
        ]
    )
    res = parse_statement(raw)
    assert len(res["transactions"]) == 4
    ind = res["indicators"]
    assert ind["nb_transactions"] == 4
    assert ind["months_covered"] == 2
    assert ind["total_in_xof"] == 350_000
    assert ind["total_out_xof"] == 130_000
    assert ind["monthly_mean_xof"] == pytest.approx(240_000.0)
    assert ind["monthly_stdev_xof"] >= 0
    assert ind["ratio_in_out"] == pytest.approx(350_000 / 130_000)


def test_parse_missing_column_raises():
    raw = b"date_iso,amount\n2026-04-01,1000\n"
    with pytest.raises(StatementParseError) as exc:
        parse_statement(raw)
    assert "colonnes manquantes" in str(exc.value)


def test_parse_invalid_direction():
    raw = _csv(["2026-04-01,1000,sideways,x"])
    with pytest.raises(StatementParseError):
        parse_statement(raw)


def test_parse_negative_amount():
    raw = _csv(["2026-04-01,-100,in,x"])
    with pytest.raises(StatementParseError):
        parse_statement(raw)


def test_parse_invalid_date():
    raw = _csv(["31-04-2026,1000,in,x"])
    with pytest.raises(StatementParseError):
        parse_statement(raw)


def test_parse_too_large_bytes():
    huge = b"x" * (MAX_BYTES + 1)
    with pytest.raises(StatementTooLargeError):
        parse_statement(huge)


def test_parse_too_many_rows():
    rows = [f"2026-04-01,{i+1},in,c" for i in range(MAX_ROWS + 5)]
    raw = _csv(rows)
    with pytest.raises(StatementTooLargeError):
        parse_statement(raw)


def test_parse_empty_file():
    with pytest.raises(StatementParseError):
        parse_statement(b"")


def test_parse_no_transactions_returns_zero_indicators():
    raw = b"date_iso,amount_xof,direction,counterparty\n"
    res = parse_statement(raw)
    assert res["transactions"] == []
    assert res["indicators"]["nb_transactions"] == 0
    assert res["indicators"]["months_covered"] == 0
    assert res["indicators"]["ratio_in_out"] is None


def test_parse_optional_counterparty_empty():
    raw = _csv(["2026-04-01,1000,in,"])
    res = parse_statement(raw)
    tx = res["transactions"][0]
    assert tx["counterparty"] is None


def test_parse_iso_datetime_accepted():
    raw = _csv(["2026-04-01T08:30:00,1500,in,c"])
    res = parse_statement(raw)
    assert res["transactions"][0]["date_iso"].startswith("2026-04-01T")
