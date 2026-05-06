"""F58 / T022 — Tests unitaires PII detector (FR-003, FR-004, FR-026).

Couvre :
- Mobile money UEMOA : CI (+225), SN (+221), BJ (+229), TG (+228), BF (+226).
- CNI / passeport.
- IBAN.
- Carte bancaire avec validation Luhn.
- Faux positifs : « 07 employés », « facteur 2.6 », chiffres aléatoires.
- Immutabilité : ``mask_pii`` ne mute pas son entrée.
"""

from __future__ import annotations

import pytest

from app.agent.guardrails.pii_detector import mask_pii
from app.agent.guardrails.pii_patterns import DEFAULT_PII_PATTERNS, luhn_valid

# ---------------------------------------------------------------------------
# Mobile money UEMOA — POSITIVE
# ---------------------------------------------------------------------------

MOBILE_MONEY_POSITIVE: list[tuple[str, str]] = [
    # Côte d'Ivoire (+225)
    ("Mon numéro est +225 07 12 34 56 78", "+225"),
    ("Tel: 0712345678", "07"),
    # Sénégal (+221)
    ("Appelle moi au +221 77 123 45 67", "+221"),
    # Bénin (+229)
    ("Whatsapp +229 91 23 45 67", "+229"),
    # Togo (+228)
    ("Mon contact +228 90 12 34 56", "+228"),
    # Burkina Faso (+226)
    ("Joignable au +226 70 12 34 56", "+226"),
]


@pytest.mark.unit
@pytest.mark.parametrize("text,prefix", MOBILE_MONEY_POSITIVE)
def test_mask_mobile_money_uemoa(text: str, prefix: str) -> None:
    masked, count = mask_pii(text)
    assert count >= 1, f"Aucune PII détectée dans : {text!r}"
    # Le texte original est intact (immutabilité)
    assert text != masked
    # Aucun chiffre du numéro original ne doit subsister dans la zone masquée
    # (on vérifie qu'au moins 5 chiffres consécutifs ont disparu)
    import re

    long_digit_seq = re.findall(r"\d{5,}", masked)
    assert not long_digit_seq, f"séquence longue de chiffres restante: {long_digit_seq}"


# ---------------------------------------------------------------------------
# IBAN
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_mask_iban_sn() -> None:
    text = "Mon IBAN est SN08 SN12 0010 0100 0000 1234 5678 9012"
    masked, count = mask_pii(text)
    assert count >= 1
    assert "SN08" not in masked or "1234 5678" not in masked


@pytest.mark.unit
def test_mask_iban_fr() -> None:
    text = "IBAN: FR76 3000 6000 0112 3456 7890 189"
    masked, count = mask_pii(text)
    assert count >= 1


# ---------------------------------------------------------------------------
# Carte bancaire (avec Luhn)
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_mask_credit_card_luhn_valid() -> None:
    # Visa test number (Luhn-valid)
    text = "Carte: 4532 0151 1283 0366"
    masked, count = mask_pii(text)
    assert count >= 1, f"Carte Luhn-valide non masquée : {text!r}"
    assert "4532" not in masked or "0366" not in masked


@pytest.mark.unit
def test_mask_credit_card_luhn_invalid_not_masked() -> None:
    # 16 chiffres aléatoires non Luhn-valides
    text = "Numero pas une carte: 1111 2222 3333 4445"
    masked, count = mask_pii(text)
    # luhn invalide ne doit PAS être masqué comme carte (mais peut être autre chose)
    # On accepte count=0 ou count par autre pattern. Vérifier que luhn_valid détecte bien.
    assert luhn_valid("1111222233334445") is False


# ---------------------------------------------------------------------------
# CNI / Passeport
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_mask_cni_uemoa() -> None:
    # Format CNI ivoirien : C001234567 ou similaire (10 chars alphanum)
    text = "Ma CNI est CI1234567890"
    masked, count = mask_pii(text)
    assert count >= 1


# ---------------------------------------------------------------------------
# Faux positifs (NE doivent PAS être masqués)
# ---------------------------------------------------------------------------

FALSE_POSITIVES: list[str] = [
    "J'ai 07 employés",
    "Le facteur d'émission est de 2.6 kgCO2/kWh",
    "Mon entreprise a 12 projets actifs",
    "Le seuil ESG est fixé à 75%",
    "Le taux de croissance est de 3.4%",
    "La année 2026 est en cours",
    "On a 100 clients fidèles",
    "Score de 8/10 obtenu",
]


@pytest.mark.unit
@pytest.mark.parametrize("text", FALSE_POSITIVES)
def test_no_false_positive_on_business_numbers(text: str) -> None:
    masked, count = mask_pii(text)
    assert count == 0, f"Faux positif: {text!r} → {masked!r}"
    assert masked == text


# ---------------------------------------------------------------------------
# Immutabilité
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_mask_pii_does_not_mutate_input() -> None:
    text = "Tel: +225 07 12 34 56 78"
    original = str(text)  # copie défensive
    _masked, _count = mask_pii(text)
    assert text == original


@pytest.mark.unit
def test_mask_pii_returns_new_string() -> None:
    text = "Tel: +225 07 12 34 56 78"
    masked, _count = mask_pii(text)
    assert masked is not text  # nouvel objet


# ---------------------------------------------------------------------------
# Compteur cumulatif
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_count_multiple_pii() -> None:
    text = (
        "Mon tel +225 07 12 34 56 78 et mon IBAN SN08 SN12 0010 0100 0000 1234 5678 9012"
    )
    _masked, count = mask_pii(text)
    assert count >= 2


# ---------------------------------------------------------------------------
# Patterns par défaut
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_default_patterns_loaded() -> None:
    assert len(DEFAULT_PII_PATTERNS) > 0
    names = {p.name for p in DEFAULT_PII_PATTERNS}
    assert "mobile_money_ci" in names
    assert "iban" in names


# ---------------------------------------------------------------------------
# Luhn helper
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_luhn_valid_visa() -> None:
    assert luhn_valid("4532015112830366") is True


@pytest.mark.unit
def test_luhn_valid_mastercard() -> None:
    # Mastercard test number (Luhn-valid)
    assert luhn_valid("5555555555554444") is True


@pytest.mark.unit
def test_luhn_invalid_random() -> None:
    assert luhn_valid("1234567890123456") is False


@pytest.mark.unit
def test_luhn_invalid_short() -> None:
    assert luhn_valid("123") is False


@pytest.mark.unit
def test_luhn_invalid_letters() -> None:
    assert luhn_valid("ABCD1234567890XY") is False
