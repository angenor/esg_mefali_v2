"""F24 — Tests unitaires du générateur PDF (reportlab)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.rapports.pdf_builder import (
    PDF_HEADER,
    IndicatorEntry,
    RapportPayload,
    ReferentielSection,
    _fmt_coverage,
    _fmt_pct,
    _md_to_paragraphs,
    _styles,
    build_pdf,
    is_pdf,
)


def _payload(
    *, sections: list[ReferentielSection] | None = None
) -> RapportPayload:
    return RapportPayload(
        rapport_id=uuid.UUID("00000000-0000-0000-0000-000000000001"),
        entreprise_name="Acme SA",
        generated_at=datetime(2026, 4, 29, 10, 0, tzinfo=UTC),
        language="fr",
        sections=sections or [],
        sources_appendix_md="# Annexe Sources\n\n- Test source\n",
    )


class TestFormatHelpers:
    def test_fmt_pct_none(self) -> None:
        assert _fmt_pct(None) == "—"

    def test_fmt_pct_value(self) -> None:
        assert _fmt_pct(72.5) == "72.5"

    def test_fmt_coverage_none(self) -> None:
        assert _fmt_coverage(None) == "—"

    def test_fmt_coverage_value(self) -> None:
        assert _fmt_coverage(0.8) == "80 %"


class TestMdToParagraphs:
    def test_empty_returns_empty(self) -> None:
        out = _md_to_paragraphs("", _styles())
        assert isinstance(out, list)

    def test_handles_h1_h2_list_text(self) -> None:
        md = "# Titre\n## Sous-titre\n- item 1\nparagraphe libre"
        out = _md_to_paragraphs(md, _styles())
        assert len(out) == 4


class TestBuildPdf:
    def test_pdf_header(self) -> None:
        data = build_pdf(_payload())
        assert isinstance(data, bytes)
        assert data.startswith(PDF_HEADER)
        assert is_pdf(data)

    def test_pdf_contains_company_name(self) -> None:
        data = build_pdf(_payload())
        assert b"Acme" in data

    def test_pdf_with_sections(self) -> None:
        sections = [
            ReferentielSection(
                code="ESG_MEFALI",
                version=1,
                score_global=72.5,
                coverage_ratio=0.8,
                scores_by_pillar={"E": 70, "S": 75, "G": 72},
                points_forts=[
                    IndicatorEntry(code="IND01", pillar="E", contribution=80.0)
                ],
                lacunes=[
                    IndicatorEntry(
                        code="IND02", pillar="S", reason="value_absent"
                    )
                ],
            ),
        ]
        data = build_pdf(_payload(sections=sections))
        assert is_pdf(data)
        assert len(data) > 1000

    def test_pdf_empty_sections(self) -> None:
        assert is_pdf(build_pdf(_payload(sections=[])))

    def test_pdf_empty_appendix(self) -> None:
        payload = RapportPayload(
            rapport_id=uuid.UUID("00000000-0000-0000-0000-000000000002"),
            entreprise_name="Acme",
            generated_at=datetime(2026, 4, 29, tzinfo=UTC),
            language="fr",
            sections=[],
            sources_appendix_md="",
        )
        assert is_pdf(build_pdf(payload))
