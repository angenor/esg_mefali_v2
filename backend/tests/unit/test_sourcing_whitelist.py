"""F56 / T051 — Tests unit de la whitelist (FR-014)."""

from __future__ import annotations

import pytest

from app.agent.sourcing.whitelist import WHITELIST_PATTERNS, is_whitelisted


@pytest.mark.unit
def test_whitelist_has_at_least_20_patterns() -> None:
    assert len(WHITELIST_PATTERNS) >= 20, (
        f"expected ≥20 patterns, got {len(WHITELIST_PATTERNS)}"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "sentence",
    [
        "En général, les PME africaines manquent de formation.",
        "Cela dépend de votre situation.",
        "Typiquement, on observe ce comportement.",
        "Selon le cas, la réponse varie.",
        "Si vous avez plus de questions, demandez-moi.",
        "À mon avis, c'est une bonne idée.",
        "Il est généralement admis que les PME bénéficient de mentorat.",
        "Globalement, les financements verts progressent.",
        "Les PME en général sont diverses.",
        "Imaginons que vous deviez choisir.",
        "Souvent, les démarches sont longues.",
        "En théorie, le processus est rapide.",
        "Habituellement, on procède ainsi.",
        "Parfois, la réponse est inattendue.",
        "Cela peut varier selon les conditions.",
        "Globalement parlant, c'est efficace.",
        "Dans la plupart des cas, ça marche.",
        "Bien entendu, chaque situation est unique.",
        "On peut considérer plusieurs options.",
        "Vous pouvez explorer cette piste.",
    ],
)
def test_known_pedagogic_phrases_are_whitelisted(sentence: str) -> None:
    assert is_whitelisted(sentence), f"expected whitelist hit on: {sentence!r}"


@pytest.mark.unit
@pytest.mark.parametrize(
    "sentence",
    [
        "Le seuil de 50 M USD est requis.",
        "L'ADEME estime à 6.0 kg CO2/litre.",
        "Le BOAD acceptera votre dossier en 8 semaines.",
        "Le facteur d'émission diesel est 6.0 kg CO2/litre.",
        "GCF accepte les PME entre 50 M et 100 M USD.",
    ],
)
def test_real_claims_not_whitelisted(sentence: str) -> None:
    assert not is_whitelisted(sentence), (
        f"unexpected whitelist hit on real claim: {sentence!r}"
    )


@pytest.mark.unit
def test_each_pattern_compiles() -> None:
    """Chaque pattern doit être compilable (regex valide)."""
    for p in WHITELIST_PATTERNS:
        assert hasattr(p, "search"), f"pattern not compiled: {p!r}"
