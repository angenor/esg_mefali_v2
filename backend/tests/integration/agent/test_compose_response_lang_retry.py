"""F58 / US3 — Tests de retry FR sur compose_response (FR-005, FR-006).

Vérifie que :
- locale=fr + LLM dérive en/es/ar → REINVOKE_LLM avec consigne FR.
- locale=fr + retry déjà consommé → fallback FR.
- locale=fr + LLM en français → pas de retry, pas de language_corrected.
- locale=en (offre EN) + LLM en anglais → pas de retry.
- texte court → pas de retry (tolérance détecteur).
"""

from __future__ import annotations

from unittest.mock import patch
from uuid import uuid4

import pytest

from app.agent.nodes.compose_response import node_compose_response
from app.agent.state import AgentState, ContextJson


def _state(
    *,
    text: str,
    locale: str = "fr",
    lang_retry_count: int = 0,
    sourcing_retry_count: int = 0,
) -> AgentState:
    return AgentState(
        thread_id=f"{uuid4()}:{uuid4()}",
        account_id=uuid4(),
        user_id=uuid4(),
        user_message="bonjour",
        context_json=ContextJson(page_route="/chat", locale=locale),  # type: ignore[arg-type]
        llm_response_text=text,
        sourcing_retry_count=sourcing_retry_count,
        lang_retry_count=lang_retry_count,
        validated_calls=[],
    )


def _settings_off():
    class _S:
        LLM_AGENT_SOURCING_MODE = "off"

    return _S()


@pytest.mark.integration
async def test_lang_drift_triggers_retry_with_french_system_message() -> None:
    """locale=fr + texte EN → retry avec SystemMessage FR + counter incrémenté."""
    text_en = (
        "This is a complete English answer about ESG with enough characters "
        "for langdetect to identify the language reliably without ambiguity."
    )
    state = _state(text=text_en, locale="fr")
    with patch(
        "app.agent.nodes.compose_response.get_settings",
        return_value=_settings_off(),
    ):
        # mode=off bypass le validator sourcing → on testerait pas le retry
        # FR. On utilise mode=permissive pour que decision='accept' soit
        # produit, ce qui déclenche notre branch lang.
        pass

    # Mode permissive (decision='accept' → branch lang)
    class _SP:
        LLM_AGENT_SOURCING_MODE = "permissive"

    with patch(
        "app.agent.nodes.compose_response.get_settings",
        return_value=_SP(),
    ):
        out = await node_compose_response(state)

    assert out["final_text"] == ""
    assert out["sourcing_decision"] == "retry"
    assert out["lang_retry_count"] == 1
    assert out["language_corrected"] is True
    assert "messages" in out
    assert len(out["messages"]) == 1
    msg_content = out["messages"][0].content
    assert "français" in msg_content.lower()


@pytest.mark.integration
async def test_lang_retry_exhausted_falls_back_to_french_text() -> None:
    """locale=fr + retry déjà consommé → fallback FR poli."""
    text_en = (
        "This still answers in English even after the retry was requested. "
        "We expect a graceful French fallback rather than serving non-FR."
    )
    state = _state(text=text_en, locale="fr", lang_retry_count=1)

    class _SP:
        LLM_AGENT_SOURCING_MODE = "permissive"

    with patch(
        "app.agent.nodes.compose_response.get_settings",
        return_value=_SP(),
    ):
        out = await node_compose_response(state)

    assert out["sourcing_decision"] == "fallback"
    assert out["language_corrected"] is True
    # Le fallback est en français
    assert "français" in out["final_text"].lower()
    # Pas de message à propager — le retry est terminé.
    assert "messages" not in out


@pytest.mark.integration
async def test_french_response_no_retry() -> None:
    """locale=fr + texte FR → pas de retry, pas de language_corrected."""
    text_fr = (
        "Voici une réponse complète en français sur les enjeux ESG des "
        "PME ouest-africaines, avec assez de caractères pour permettre "
        "à langdetect de fonctionner correctement."
    )
    state = _state(text=text_fr, locale="fr")

    class _SP:
        LLM_AGENT_SOURCING_MODE = "permissive"

    with patch(
        "app.agent.nodes.compose_response.get_settings",
        return_value=_SP(),
    ):
        out = await node_compose_response(state)

    assert out["final_text"] == text_fr
    assert out.get("language_corrected", False) is False
    assert out.get("lang_retry_count", 0) == 0


@pytest.mark.integration
async def test_locale_en_does_not_force_french_retry() -> None:
    """locale=en + texte EN → pas de retry FR (offre autorise EN)."""
    text_en = (
        "This English answer is fine because the user's locale and offer "
        "explicitly accept English as the response language."
    )
    state = _state(text=text_en, locale="en")

    class _SP:
        LLM_AGENT_SOURCING_MODE = "permissive"

    with patch(
        "app.agent.nodes.compose_response.get_settings",
        return_value=_SP(),
    ):
        out = await node_compose_response(state)

    assert out["final_text"] == text_en
    assert out.get("language_corrected", False) is False


@pytest.mark.integration
async def test_short_text_skips_lang_check() -> None:
    """Texte trop court → pas de retry (détecteur retourne 'unknown')."""
    state = _state(text="OK", locale="fr")

    class _SP:
        LLM_AGENT_SOURCING_MODE = "permissive"

    with patch(
        "app.agent.nodes.compose_response.get_settings",
        return_value=_SP(),
    ):
        out = await node_compose_response(state)

    assert out["final_text"] == "OK"
    assert out.get("language_corrected", False) is False
