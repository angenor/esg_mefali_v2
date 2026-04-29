"""F24 — Générateur de PDF (reportlab platypus).

API publique : :func:`build_pdf`. Sans état, renvoie les bytes d'un PDF prêt
à être streamé ou écrit sur disque. Les graphiques radar sont embarqués
sous forme de PNG (cf. :mod:`app.rapports.radar`).

Layout MVP (sans Jinja2) :
- Page 1 : couverture (titre, identité PME, date, rapport_id).
- Pages 2..N : 1 section par référentiel (score global, radar, points forts,
  lacunes).
- Annexe : Sources & références (markdown -> paragraphes).
"""

from __future__ import annotations

import io
import uuid
from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (
    Image,
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.rapports.radar import render_radar_png


@dataclass(frozen=True)
class IndicatorEntry:
    code: str
    pillar: str
    value: float | int | str | None = None
    contribution: float | None = None
    reason: str | None = None  # pour les manquants


@dataclass(frozen=True)
class ReferentielSection:
    code: str
    version: int
    score_global: float | None
    coverage_ratio: float | None
    scores_by_pillar: Mapping[str, float]
    points_forts: list[IndicatorEntry] = field(default_factory=list)
    lacunes: list[IndicatorEntry] = field(default_factory=list)


@dataclass(frozen=True)
class RapportPayload:
    rapport_id: uuid.UUID
    entreprise_name: str
    generated_at: datetime
    language: str
    sections: list[ReferentielSection]
    sources_appendix_md: str = ""


# --- Styles ---------------------------------------------------------------


def _styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "title",
            parent=base["Title"],
            fontSize=24,
            leading=28,
            spaceAfter=16,
        ),
        "h1": ParagraphStyle(
            "h1",
            parent=base["Heading1"],
            fontSize=16,
            leading=20,
            spaceBefore=12,
            spaceAfter=8,
        ),
        "h2": ParagraphStyle(
            "h2",
            parent=base["Heading2"],
            fontSize=12,
            leading=15,
            spaceBefore=8,
            spaceAfter=4,
        ),
        "body": ParagraphStyle(
            "body",
            parent=base["BodyText"],
            fontSize=10,
            leading=13,
        ),
        "muted": ParagraphStyle(
            "muted",
            parent=base["BodyText"],
            fontSize=9,
            leading=12,
            textColor=colors.grey,
        ),
    }


# --- Helpers --------------------------------------------------------------


def _fmt_pct(v: float | None, *, decimals: int = 1) -> str:
    if v is None:
        return "—"
    return f"{v:.{decimals}f}"


def _fmt_coverage(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v * 100:.0f} %"


def _md_to_paragraphs(md: str, styles: Mapping[str, ParagraphStyle]) -> list:
    """Conversion ultra-light markdown -> Paragraph reportlab.

    Supporte : titres ``# ``, ``## `` et listes ``- ``. Les paragraphes texte
    sont rendus tels quels (reportlab tolère un sous-ensemble HTML).
    """
    out: list = []
    for raw in md.splitlines():
        line = raw.rstrip()
        if not line:
            out.append(Spacer(1, 0.2 * cm))
            continue
        if line.startswith("# "):
            out.append(Paragraph(line[2:], styles["h1"]))
            continue
        if line.startswith("## "):
            out.append(Paragraph(line[3:], styles["h2"]))
            continue
        if line.startswith("- "):
            out.append(Paragraph(f"• {line[2:]}", styles["body"]))
            continue
        out.append(Paragraph(line, styles["body"]))
    return out


# --- Sections --------------------------------------------------------------


def _cover_story(
    payload: RapportPayload, styles: Mapping[str, ParagraphStyle]
) -> list:
    items: list = [
        Spacer(1, 3 * cm),
        Paragraph("Rapport de Conformité ESG", styles["title"]),
        Spacer(1, 0.5 * cm),
        Paragraph(payload.entreprise_name, styles["h1"]),
        Spacer(1, 0.3 * cm),
        Paragraph(
            f"Date de génération : {payload.generated_at:%Y-%m-%d %H:%M UTC}",
            styles["body"],
        ),
        Paragraph(f"Identifiant rapport : {payload.rapport_id}", styles["muted"]),
        Paragraph(f"Langue : {payload.language}", styles["muted"]),
        Spacer(1, 1 * cm),
        Paragraph(
            "Ce rapport synthétise les scores ESG de l'entreprise sur les "
            "référentiels sélectionnés. Toutes les sources mobilisées figurent "
            "en annexe.",
            styles["body"],
        ),
        PageBreak(),
    ]
    return items


def _summary_table(
    sections: Iterable[ReferentielSection],
    styles: Mapping[str, ParagraphStyle],
) -> Table:
    data = [["Référentiel", "Version", "Score global", "Couverture"]]
    for s in sections:
        data.append(
            [
                s.code,
                str(s.version),
                _fmt_pct(s.score_global),
                _fmt_coverage(s.coverage_ratio),
            ]
        )
    table = Table(
        data, hAlign="LEFT", colWidths=[5 * cm, 2 * cm, 3 * cm, 3 * cm]
    )
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("FONTSIZE", (0, 0), (-1, -1), 9),
                ("GRID", (0, 0), (-1, -1), 0.25, colors.grey),
                ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ]
        )
    )
    return table


def _section_story(
    section: ReferentielSection, styles: Mapping[str, ParagraphStyle]
) -> list:
    items: list = [
        Paragraph(
            f"Référentiel {section.code} (v{section.version})", styles["h1"]
        ),
        Paragraph(
            f"Score global : <b>{_fmt_pct(section.score_global)}</b> / 100 — "
            f"Couverture : {_fmt_coverage(section.coverage_ratio)}",
            styles["body"],
        ),
        Spacer(1, 0.3 * cm),
    ]

    try:
        png_bytes = render_radar_png(
            section.scores_by_pillar,
            title=f"{section.code} — Score par pilier",
        )
        items.append(Image(io.BytesIO(png_bytes), width=8 * cm, height=8 * cm))
    except Exception:  # pragma: no cover - défensif
        items.append(Paragraph("[radar indisponible]", styles["muted"]))
    items.append(Spacer(1, 0.3 * cm))

    items.append(Paragraph("Points forts", styles["h2"]))
    if not section.points_forts:
        items.append(
            Paragraph(
                "Aucun indicateur au-dessus du seuil.", styles["muted"]
            )
        )
    else:
        for ind in section.points_forts:
            items.append(
                Paragraph(
                    f"• <b>{ind.code}</b> ({ind.pillar}) — contribution "
                    f"{_fmt_pct(ind.contribution)}",
                    styles["body"],
                )
            )

    items.append(Spacer(1, 0.2 * cm))
    items.append(Paragraph("Lacunes à combler", styles["h2"]))
    if not section.lacunes:
        items.append(Paragraph("Aucune lacune détectée.", styles["muted"]))
    else:
        for ind in section.lacunes:
            reason = ind.reason or "—"
            items.append(
                Paragraph(
                    f"• <b>{ind.code}</b> ({ind.pillar}) — {reason}",
                    styles["body"],
                )
            )

    items.append(PageBreak())
    return items


def _appendix_story(md: str, styles: Mapping[str, ParagraphStyle]) -> list:
    if not md.strip():
        return [
            Paragraph("Annexe Sources", styles["h1"]),
            Paragraph("Aucune source référencée.", styles["muted"]),
        ]
    return _md_to_paragraphs(md, styles)


# --- Public API -----------------------------------------------------------


def build_pdf(payload: RapportPayload) -> bytes:
    """Construit le PDF complet et renvoie les bytes."""
    styles = _styles()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=2 * cm,
        rightMargin=2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=f"Rapport ESG {payload.entreprise_name}",
        author="ESG Mefali",
    )

    story: list = []
    story.extend(_cover_story(payload, styles))

    story.append(Paragraph("Synthèse", styles["h1"]))
    if payload.sections:
        story.append(_summary_table(payload.sections, styles))
    else:
        story.append(
            Paragraph(
                "Aucun référentiel sélectionné — rapport vide.",
                styles["muted"],
            )
        )
    story.append(PageBreak())

    for section in payload.sections:
        story.extend(_section_story(section, styles))

    story.extend(_appendix_story(payload.sources_appendix_md, styles))

    doc.build(story)
    return buffer.getvalue()


PDF_HEADER = b"%PDF-"


def is_pdf(data: bytes) -> bool:
    """Helper pour les tests : vérifie le magic header PDF."""
    return data.startswith(PDF_HEADER)
