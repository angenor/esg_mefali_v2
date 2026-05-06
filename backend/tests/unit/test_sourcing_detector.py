"""F56 / T027 — Unit tests pour ``app.agent.sourcing.detector``.

TDD : tests rouges avant implémentation.

Couverture exigée par ``contracts/sourcing-validator.md`` :
- ≥ 3 cas positifs par ``ClaimKind``.
- Whitelist hit → liste vide pour la phrase.
- ``from_tool=True`` quand la sous-chaîne matche ``tool_outputs``.
"""

from __future__ import annotations

import pytest

from app.agent.sourcing.detector import detect_claims
from app.agent.sourcing.models import Claim


def _kinds(claims: list[Claim]) -> list[str]:
    return [c.kind for c in claims]


@pytest.mark.unit
class TestNumberWithUnit:
    def test_kg_co2_per_litre(self) -> None:
        claims = detect_claims(
            "Le facteur ADEME est de 6.0 kg CO2/litre pour le diesel."
        )
        # ≥1 number_with_unit + 1 reference_keyword (ADEME)
        assert any(c.kind == "number_with_unit" for c in claims), (
            f"missing number_with_unit; got {_kinds(claims)}"
        )
        assert any(c.kind == "reference_keyword" for c in claims)

    def test_million_usd(self) -> None:
        claims = detect_claims("Le seuil est de 50 M USD.")
        assert any(c.kind == "number_with_unit" for c in claims)

    def test_kwh_yearly(self) -> None:
        claims = detect_claims("Production annuelle de 1200 kWh.")
        assert any(c.kind == "number_with_unit" for c in claims)


@pytest.mark.unit
class TestPercentage:
    def test_percentage_simple(self) -> None:
        claims = detect_claims("La réduction attendue est de 15%.")
        assert any(c.kind == "percentage" for c in claims)

    def test_percentage_decimal(self) -> None:
        claims = detect_claims("Taux d'intérêt de 4,5 %.")
        assert any(c.kind == "percentage" for c in claims)

    def test_percentage_word(self) -> None:
        claims = detect_claims("Une réduction de 20 pour cent.")
        assert any(c.kind == "percentage" for c in claims)


@pytest.mark.unit
class TestRange:
    def test_range_million(self) -> None:
        claims = detect_claims("Entre 50 et 100 millions USD.")
        assert any(c.kind == "range" for c in claims)

    def test_range_dash(self) -> None:
        claims = detect_claims("Le délai est de 6-12 semaines.")
        assert any(c.kind == "range" for c in claims)

    def test_range_with_to(self) -> None:
        claims = detect_claims("De 5 à 10 ans.")
        assert any(c.kind == "range" for c in claims)


@pytest.mark.unit
class TestRatio:
    def test_ratio_per(self) -> None:
        claims = detect_claims("Le rapport est de 3:1.")
        assert any(c.kind == "ratio" for c in claims)

    def test_ratio_words(self) -> None:
        claims = detect_claims("Un ratio de 1 pour 4.")
        assert any(c.kind == "ratio" for c in claims)

    def test_ratio_explicit(self) -> None:
        claims = detect_claims("La proportion 2/3 est observée.")
        assert any(c.kind == "ratio" for c in claims)


@pytest.mark.unit
class TestReferenceKeyword:
    def test_ademe(self) -> None:
        claims = detect_claims("Source ADEME pour le diesel.")
        assert any(c.kind == "reference_keyword" for c in claims)

    def test_gcf(self) -> None:
        claims = detect_claims("Le programme GCF accepte les PME.")
        assert any(c.kind == "reference_keyword" for c in claims)

    def test_boad(self) -> None:
        claims = detect_claims("Le BOAD finance ce projet.")
        assert any(c.kind == "reference_keyword" for c in claims)


@pytest.mark.unit
class TestThreshold:
    def test_threshold_seuil(self) -> None:
        claims = detect_claims("Le seuil GCF est de 50 M USD.")
        assert any(c.kind == "threshold" for c in claims)

    def test_threshold_minimum(self) -> None:
        claims = detect_claims("Le minimum requis est 10000 EUR.")
        assert any(c.kind == "threshold" for c in claims)

    def test_threshold_maximum(self) -> None:
        claims = detect_claims("Le plafond fixé est 1 million EUR.")
        assert any(c.kind == "threshold" for c in claims)


@pytest.mark.unit
class TestFormula:
    def test_formula_equals(self) -> None:
        claims = detect_claims("Calcul: emissions = consommation * facteur.")
        assert any(c.kind == "formula" for c in claims)

    def test_formula_simple(self) -> None:
        claims = detect_claims("On a CO2 = volume * 6.0.")
        assert any(c.kind == "formula" for c in claims)

    def test_formula_phrase(self) -> None:
        claims = detect_claims("La formule appliquée: x = a + b.")
        assert any(c.kind == "formula" for c in claims)


@pytest.mark.unit
def test_whitelist_filters_generic_pedagogic() -> None:
    """Phrase whitelistée ne doit produire aucun claim."""
    claims = detect_claims(
        "En général, les PME africaines investissent peu dans la formation."
    )
    assert claims == [], f"whitelist should swallow this; got {_kinds(claims)}"


@pytest.mark.unit
def test_whitelist_does_not_filter_real_claim() -> None:
    """Un claim chiffré ne doit pas être whitelisté à tort."""
    claims = detect_claims("Le seuil de 50 M USD du GCF s'applique.")
    assert any(c.kind == "threshold" for c in claims)
    assert any(c.kind == "number_with_unit" for c in claims)


@pytest.mark.unit
def test_from_tool_marks_claims_in_tool_outputs() -> None:
    """Les chiffres déjà présents dans tool_outputs doivent être ``from_tool=True``."""
    text = "Vous avez 12 kWh consommés ; nouvelle valeur 50 M USD."
    tool_outputs = ["Mesure récente : 12 kWh stockés en base"]
    claims = detect_claims(text, tool_outputs=tool_outputs)
    # "12 kWh" provient d'un tool_output ; "50 M USD" non.
    from_tool_claims = [c for c in claims if c.from_tool]
    not_from_tool = [c for c in claims if not c.from_tool]
    assert from_tool_claims, "expected at least one from_tool claim"
    assert not_from_tool, "expected at least one regular claim"


@pytest.mark.unit
def test_empty_text_returns_empty_list() -> None:
    assert detect_claims("") == []


@pytest.mark.unit
def test_claims_sorted_by_span_start() -> None:
    text = "Premier 50% puis 100 kg CO2 ensuite."
    claims = detect_claims(text)
    starts = [c.span[0] for c in claims]
    assert starts == sorted(starts)


@pytest.mark.unit
def test_no_overlapping_claims_same_kind() -> None:
    """Si deux matches ont le même span exact, on dédup."""
    claims = detect_claims("Réduction de 50% par an.")
    seen = set()
    for c in claims:
        key = (c.span, c.kind)
        assert key not in seen, f"duplicate claim {key}"
        seen.add(key)
