"""F58 / T029 — Tests unitaires lang_check (FR-005, FR-006)."""

from __future__ import annotations

import pytest

from app.agent.guardrails.lang_check import detect_language, needs_french_retry


@pytest.mark.unit
def test_detect_language_fr() -> None:
    text = "Bonjour, j'aimerais des conseils sur ma candidature ESG en finance verte."
    assert detect_language(text) == "fr"


@pytest.mark.unit
def test_detect_language_en() -> None:
    text = "Hello, I would like some advice on my green finance ESG application."
    assert detect_language(text) == "en"


@pytest.mark.unit
def test_detect_language_short_text_returns_unknown() -> None:
    # Texte trop court → fallback unknown
    assert detect_language("OK") == "unknown"
    assert detect_language("") == "unknown"


@pytest.mark.unit
def test_detect_language_fr_with_technical_terms() -> None:
    # FR avec termes techniques EN ne doit PAS être classé EN
    text = (
        "Notre API utilise les indicateurs ESG du référentiel UE pour calculer "
        "les KPI environnementaux."
    )
    assert detect_language(text) == "fr"


# ---------------------------------------------------------------------------
# needs_french_retry
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_needs_french_retry_when_en_and_pref_fr() -> None:
    assert needs_french_retry("en", "fr", offer_accepted_langs=None) is True


@pytest.mark.unit
def test_no_retry_when_lang_already_fr() -> None:
    assert needs_french_retry("fr", "fr", offer_accepted_langs=None) is False


@pytest.mark.unit
def test_no_retry_when_pref_not_fr() -> None:
    assert needs_french_retry("en", "en", offer_accepted_langs=None) is False


@pytest.mark.unit
def test_no_retry_when_offer_accepts_detected_lang() -> None:
    # Une offre EN-acceptée doit autoriser une réponse EN même pour pref FR
    assert needs_french_retry("en", "fr", offer_accepted_langs=["en"]) is False


@pytest.mark.unit
def test_no_retry_for_unknown_lang() -> None:
    # Si on ne peut pas détecter, ne pas retry (évite boucle inutile)
    assert needs_french_retry("unknown", "fr", offer_accepted_langs=None) is False


@pytest.mark.unit
def test_retry_for_es_or_ar_when_pref_fr() -> None:
    assert needs_french_retry("es", "fr", offer_accepted_langs=None) is True
    assert needs_french_retry("ar", "fr", offer_accepted_langs=None) is True
