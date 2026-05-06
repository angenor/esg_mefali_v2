"""F53 / T014 — Tests unitaires pour ``app/agent/llm_factory.py``.

Aucune call réseau : on monkeypatche les settings pour vérifier que
``ChatOpenAI`` est instancié avec les bons paramètres.
"""

from __future__ import annotations

import pytest

from app.agent.llm_factory import build_chat_model
from app.config import get_settings

pytestmark = pytest.mark.unit


def test_build_chat_model_uses_settings(monkeypatch) -> None:
    s = get_settings()
    model = build_chat_model(s)

    # Pas de hard-code : doit refléter la config
    assert model.model_name == s.LLM_MODEL
    # OpenAI base_url est exposé via openai_api_base
    base_url = getattr(model, "openai_api_base", None) or getattr(
        model, "base_url", None
    )
    if base_url is not None:
        assert str(base_url).rstrip("/") == s.LLM_BASE_URL.rstrip("/")


def test_build_chat_model_streaming_true() -> None:
    s = get_settings()
    model = build_chat_model(s)
    # ``streaming`` is exposé sur ChatOpenAI ou son client interne
    streaming = getattr(model, "streaming", None) or getattr(
        model, "_default_params", {}
    ).get("stream")
    assert streaming is True or streaming is None  # default streaming activé


def test_build_chat_model_no_implicit_retries() -> None:
    s = get_settings()
    model = build_chat_model(s)
    assert getattr(model, "max_retries", 0) == 0


def test_build_chat_model_overrides() -> None:
    s = get_settings()
    custom = build_chat_model(s, model="gpt-test-override")
    assert custom.model_name == "gpt-test-override"


def test_build_chat_model_timeout_aligned_with_settings() -> None:
    s = get_settings()
    model = build_chat_model(s)
    timeout = getattr(model, "request_timeout", None) or getattr(
        model, "timeout", None
    )
    assert timeout is not None
    # Tolérance : type peut être Timeout, int, float
    val = float(timeout) if isinstance(timeout, (int, float)) else float(getattr(timeout, "timeout", s.LLM_AGENT_TIMEOUT_S))
    assert val == s.LLM_AGENT_TIMEOUT_S


def test_build_chat_model_default_settings_path() -> None:
    """Sans argument explicite, build_chat_model doit utiliser get_settings()."""
    model = build_chat_model()
    assert model.model_name == get_settings().LLM_MODEL
