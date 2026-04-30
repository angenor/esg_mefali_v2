"""F26 - Unit tests for the heuristic dossier generator (pure function)."""

from __future__ import annotations

import pytest

from app.dossier.generator import generate_dossier
from app.dossier.schemas import DossierResponse


@pytest.mark.unit
def test_generate_with_empty_projet() -> None:
    """Empty projet still yields a valid dossier with default fallbacks."""
    out = generate_dossier({}, {}, None)
    assert isinstance(out, DossierResponse)
    assert out.language == "fr"
    assert "resume_executif" in out.sections
    assert "Projet sans titre" in out.sections["resume_executif"]
    assert "non communique" in out.sections["resume_executif"]
    assert out.sources == []
    assert out.metadata["skill_sections_count"] == 0


@pytest.mark.unit
def test_generate_with_full_projet() -> None:
    """Full projet + offre populates resume, contexte, alignement, plan."""
    projet = {
        "titre": "Centrale solaire de Thies",
        "description": "Installation de 10 MW photovoltaiques.",
        "montant": "5000000",
        "devise": "EUR",
    }
    offre = {"nom": "Offre verte BOAD", "fonds_nom": "BOAD", "secteur": "energie"}
    out = generate_dossier(projet, offre, None)

    assert "Centrale solaire de Thies" in out.sections["resume_executif"]
    assert "5 000 000 EUR" in out.sections["resume_executif"]
    assert "Offre verte BOAD" in out.sections["resume_executif"]
    assert "BOAD" in out.sections["resume_executif"]
    assert "energie" in out.sections["contexte"]
    assert "ESG" in out.sections["alignement_esg"]
    assert "1." in out.sections["plan_action"]
    assert out.language == "fr"


@pytest.mark.unit
def test_generate_converts_fcfa_to_eur() -> None:
    """Montant in XOF/FCFA is rendered with an EUR conversion hint."""
    projet = {"titre": "P", "montant": "655957", "devise": "XOF"}
    out = generate_dossier(projet, {}, None)
    resume = out.sections["resume_executif"]
    assert "FCFA" in resume
    assert "EUR" in resume
    # 655 957 XOF == 1 000 EUR (peg).
    assert "1 000" in resume or "1000" in resume


@pytest.mark.unit
def test_generate_language_is_fr_only() -> None:
    """Generator forces language='fr' regardless of inputs (MVP)."""
    out = generate_dossier({"titre": "X"}, {"nom": "Y"}, None)
    assert out.language == "fr"


@pytest.mark.unit
def test_generate_extracts_skill_sections_and_sources() -> None:
    """Skill template '#' headings become recommendations; sources flow through."""
    skill = {
        "template": "# Resume executif\n# Contexte projet\n## Alignement\n",
        "sources": [
            {"label": "GCF Investment Framework", "url": "https://example.org/gcf"},
            {"label": "BOAD Procedures", "url": None},
        ],
    }
    out = generate_dossier({"titre": "P"}, {"nom": "O"}, skill)

    assert out.metadata["skill_sections_count"] == 3
    recos = out.sections["skill_recommendations"]
    assert "Resume executif" in recos
    assert "Contexte projet" in recos
    assert "Alignement" in recos

    assert len(out.sources) == 2
    labels = [s.label for s in out.sources]
    assert "GCF Investment Framework" in labels
    assert "BOAD Procedures" in labels
    assert out.sources[0].url == "https://example.org/gcf"
    assert out.sources[1].url is None
