"""F26 - Pure heuristic generator for candidature dossiers (MVP stub).

No LLM call - text templates only. FR language only.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.dossier.schemas import DossierResponse, DossierSource

# FCFA -> EUR fixed parity (XOF/XAF pegged to EUR via CFA franc).
FCFA_PER_EUR = Decimal("655.957")


def _get(obj: Any, key: str, default: Any = None) -> Any:
    """Read attribute or dict key tolerantly."""
    if obj is None:
        return default
    if isinstance(obj, dict):
        return obj.get(key, default)
    return getattr(obj, key, default)


def _format_amount(montant: Any, devise: str | None) -> str:
    """Return a human-readable amount with EUR conversion when in FCFA."""
    if montant is None:
        return "non communique"
    try:
        amount = Decimal(str(montant))
    except Exception:  # noqa: BLE001
        return str(montant)
    devise_norm = (devise or "").upper()
    if devise_norm in {"XOF", "XAF", "FCFA"}:
        eur = (amount / FCFA_PER_EUR).quantize(Decimal("1"))
        return f"{amount:,.0f} FCFA (~{eur:,} EUR)".replace(",", " ")
    if devise_norm == "EUR":
        return f"{amount:,.0f} EUR".replace(",", " ")
    return f"{amount:,.0f} {devise_norm or ''}".strip().replace(",", " ")


def _extract_skill_sections(skill: Any) -> list[str]:
    """Extract section labels from a skill's template/system_prompt."""
    if skill is None:
        return []
    template = _get(skill, "template") or _get(skill, "system_prompt") or ""
    if not isinstance(template, str):
        return []
    sections: list[str] = []
    for line in template.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            label = stripped.lstrip("#").strip()
            if label:
                sections.append(label)
    return sections


def _extract_skill_sources(skill: Any) -> list[DossierSource]:
    """Extract sources from a skill object (dict or attr)."""
    if skill is None:
        return []
    raw = _get(skill, "sources") or []
    out: list[DossierSource] = []
    for item in raw:
        if isinstance(item, dict):
            label = item.get("label") or item.get("title") or item.get("url") or ""
            url = item.get("url")
        else:
            label = _get(item, "label", "") or _get(item, "title", "") or ""
            url = _get(item, "url")
        if label:
            out.append(DossierSource(label=str(label), url=str(url) if url else None))
    return out


def generate_dossier(projet: Any, offre: Any, skill: Any = None) -> DossierResponse:
    """Generate a heuristic dossier (FR only) from projet, offre, skill.

    Pure function: no I/O, no LLM. Output sections are deterministic templates.
    """
    titre = _get(projet, "titre") or _get(projet, "title") or "Projet sans titre"
    description = _get(projet, "description") or "Description non fournie."
    montant = _get(projet, "montant")
    devise = _get(projet, "devise") or _get(projet, "currency")

    offre_nom = _get(offre, "nom") or _get(offre, "name") or "Offre cible"
    offre_fonds = _get(offre, "fonds_nom") or _get(offre, "fonds") or ""
    offre_secteur = _get(offre, "secteur") or _get(offre, "sector") or ""

    montant_str = _format_amount(montant, devise)

    resume = (
        f"Le projet '{titre}' sollicite un financement de {montant_str} "
        f"aupres de l'offre '{offre_nom}'"
        + (f" du fonds {offre_fonds}." if offre_fonds else ".")
    )

    contexte = (
        f"Description du projet : {description}\n"
        f"Secteur cible de l'offre : {offre_secteur or 'non precise'}."
    )

    alignement = (
        "Le projet s'aligne avec les criteres ESG de l'offre cible : "
        "impact environnemental positif, gouvernance documentee, "
        "indicateurs sociaux suivis."
    )

    plan_action = (
        "1. Constitution du dossier administratif.\n"
        "2. Validation des indicateurs ESG.\n"
        "3. Soumission a l'intermediaire accredite.\n"
        "4. Suivi de l'instruction et reponses aux questions."
    )

    skill_sections = _extract_skill_sections(skill)
    skill_sections_text = (
        "Sections recommandees par le skill : " + ", ".join(skill_sections)
        if skill_sections
        else "Aucune section additionnelle issue du skill."
    )

    sources = _extract_skill_sources(skill)
    sources_text = (
        "Sources : " + "; ".join(s.label for s in sources)
        if sources
        else "Sources : a completer."
    )

    sections = {
        "resume_executif": resume,
        "contexte": contexte,
        "alignement_esg": alignement,
        "plan_action": plan_action,
        "skill_recommendations": skill_sections_text,
        "sources": sources_text,
    }

    return DossierResponse(
        sections=sections,
        sources=sources,
        language="fr",
        metadata={
            "projet_titre": titre,
            "offre_nom": offre_nom,
            "skill_sections_count": len(skill_sections),
        },
    )
