"""F03 US5 — Annexe Sources auto-générée pour le rapport conformité."""

from __future__ import annotations

import uuid

from sqlalchemy import text
from sqlalchemy.orm import Session


def _format_entry(row: dict) -> str:
    parts = [f"**{row.get('title', '')}**"]
    publisher = row.get("publisher")
    if publisher:
        parts.append(f"_{publisher}_")
    version = row.get("version")
    if version:
        parts.append(f"v{version}")
    date_publi = row.get("date_publi")
    if date_publi:
        parts.append(str(date_publi))
    page = row.get("page")
    if page:
        parts.append(page)
    section = row.get("section")
    if section:
        parts.append(section)
    url = row.get("url")
    if url:
        parts.append(f"[{url}]({url})")

    incomplete = not (publisher and url)
    if incomplete:
        parts.append("[source incomplète]")
    return " — ".join(p for p in parts if p)


def build_sources_appendix(db: Session, source_ids: list[uuid.UUID]) -> str:
    """Génère un markdown dédoublonné, trié par publisher puis date_publi desc.

    Exclut les sources non ``verified``. Marque ``[source incomplète]`` si
    publisher ou url manquant (conserve la trace).
    """
    if not source_ids:
        return "# Annexe Sources\n\n_Aucune source vérifiée référencée._\n"

    deduped = list({str(s) for s in source_ids})
    placeholders = ", ".join(f":id_{i}" for i in range(len(deduped)))
    params = {f"id_{i}": deduped[i] for i in range(len(deduped))}
    rows = db.execute(
        text(
            f"SELECT id::text, url, title, publisher, version, "
            f"date_publi, page, section, verification_status "
            f"FROM source WHERE id IN ({placeholders}) "
            f"AND verification_status = 'verified'"
        ),
        params,
    ).mappings().all()

    if not rows:
        return "# Annexe Sources\n\n_Aucune source vérifiée référencée._\n"

    rows = sorted(
        rows,
        key=lambda r: (
            (r.get("publisher") or "").lower(),
            -(r.get("date_publi").toordinal() if r.get("date_publi") else 0),
            r.get("title") or "",
        ),
    )

    md_lines = ["# Annexe Sources", ""]
    for r in rows:
        md_lines.append(f"- {_format_entry(dict(r))}")
    md_lines.append("")
    return "\n".join(md_lines)


def to_pdf_section(md: str) -> str:
    """Helper de packaging pour insertion dans la pipeline PDF (F24).

    Pour l'instant : renvoie le markdown tel quel ; F24 branchera son moteur
    (e.g. WeasyPrint via markdown -> HTML).
    """
    return md
