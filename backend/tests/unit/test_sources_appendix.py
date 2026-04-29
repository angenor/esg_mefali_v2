"""F03 US5 — Tests unitaires de build_sources_appendix."""

from __future__ import annotations

import datetime
import uuid
from unittest.mock import MagicMock

import pytest

from app.utils.sources_appendix import build_sources_appendix, to_pdf_section


def _row(
    sid: uuid.UUID,
    *,
    title: str,
    publisher: str | None = "GCF",
    url: str | None = "https://gcf.example/x",
    version: str | None = None,
    date_publi: datetime.date | None = None,
    status: str = "verified",
):
    return {
        "id": str(sid),
        "url": url,
        "title": title,
        "publisher": publisher,
        "version": version,
        "date_publi": date_publi,
        "page": None,
        "section": None,
        "verification_status": status,
    }


@pytest.mark.unit
def test_empty_list_renders_empty_appendix():
    db = MagicMock()
    md = build_sources_appendix(db, [])
    assert "Aucune source vérifiée" in md


@pytest.mark.unit
def test_dedup_returns_single_entry_for_duplicates():
    db = MagicMock()
    sid = uuid.uuid4()
    db.execute.return_value.mappings.return_value.all.return_value = [
        _row(sid, title="Doc A")
    ]
    md = build_sources_appendix(db, [sid, sid, sid])
    assert md.count("Doc A") == 1


@pytest.mark.unit
def test_excludes_unverified():
    """Les non-verified sont filtrés via le WHERE — vérifie le SQL."""
    db = MagicMock()
    db.execute.return_value.mappings.return_value.all.return_value = []
    md = build_sources_appendix(db, [uuid.uuid4()])
    sql_str = str(db.execute.call_args[0][0])
    assert "verification_status = 'verified'" in sql_str
    assert "Aucune source vérifiée" in md


@pytest.mark.unit
def test_marks_incomplete_source():
    db = MagicMock()
    sid = uuid.uuid4()
    db.execute.return_value.mappings.return_value.all.return_value = [
        _row(sid, title="Incomplete", publisher=None, url=None)
    ]
    md = build_sources_appendix(db, [sid])
    assert "[source incomplète]" in md


@pytest.mark.unit
def test_sorted_by_publisher_then_date_desc():
    db = MagicMock()
    sids = [uuid.uuid4() for _ in range(3)]
    db.execute.return_value.mappings.return_value.all.return_value = [
        _row(sids[0], title="A", publisher="ZZZ", date_publi=datetime.date(2020, 1, 1)),
        _row(sids[1], title="B", publisher="AAA", date_publi=datetime.date(2024, 1, 1)),
        _row(sids[2], title="C", publisher="AAA", date_publi=datetime.date(2025, 1, 1)),
    ]
    md = build_sources_appendix(db, sids)
    # AAA first (alphabetic), with C (2025) before B (2024)
    pos_c = md.find("**C**")
    pos_b = md.find("**B**")
    pos_a = md.find("**A**")
    assert -1 < pos_c < pos_b < pos_a


@pytest.mark.unit
def test_to_pdf_section_passthrough():
    md = "# Annexe Sources\n\n- toto"
    assert to_pdf_section(md) == md
