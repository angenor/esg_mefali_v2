"""F03 US3 — Tests heuristiques de détection ESG."""

from __future__ import annotations

import pytest

from app.services.llm_validation.heuristics import detect_esg_claims


@pytest.mark.unit
@pytest.mark.parametrize(
    "msg",
    [
        "Le projet émet 12.5 tCO2e par an.",
        "La consommation est de 2400 kWh.",
        "Le ticket minimum est 5 000 000 FCFA.",
        "Coût d'investissement : 250000 EUR.",
        "Le seuil de réduction est 30%.",
        "Surface : 12 ha.",
        "Le critère GCF impose une diligence.",
        "Le seuil minimum est documenté.",
        "Le facteur d'émission du diesel est 2.68 kgCO2e/L.",
        "L'indicateur retenu est l'intensité carbone.",
        "Le référentiel GRI s'applique.",
        "La formule retenue donne 100$.",
    ],
)
def test_detects_esg_claims(msg):
    res = detect_esg_claims(msg)
    assert res.has_esg_claim is True


@pytest.mark.unit
@pytest.mark.parametrize(
    "msg",
    [
        "",
        "Bonjour, comment puis-je vous aider ?",
        "Je vais consulter les informations.",
        "Vous êtes la 3ème personne.",  # chiffre sans unité
        "Souhaitez-vous comparer plusieurs offres ?",
        "Voici la liste des étapes que nous avons couvertes.",
        "Merci de patienter.",
    ],
)
def test_no_esg_claim(msg):
    res = detect_esg_claims(msg)
    assert res.has_esg_claim is False
