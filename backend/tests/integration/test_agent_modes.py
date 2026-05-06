"""F53 / T061-T062 — Tests de bascule LLM_AGENT_MODE (US5)."""

from __future__ import annotations

import pytest

from app.config import get_settings

pytestmark = pytest.mark.integration


def test_default_mode_is_langgraph() -> None:
    settings = get_settings()
    assert settings.LLM_AGENT_MODE == "langgraph"


def test_settings_llm_agent_max_tools_default() -> None:
    settings = get_settings()
    assert settings.LLM_AGENT_MAX_TOOLS == 10


def test_settings_llm_agent_max_retries_default() -> None:
    settings = get_settings()
    assert settings.LLM_AGENT_MAX_RETRIES == 2


def test_settings_llm_agent_timeout_default() -> None:
    settings = get_settings()
    assert settings.LLM_AGENT_TIMEOUT_S == 30.0


def test_settings_llm_agent_trace_default() -> None:
    settings = get_settings()
    assert settings.LLM_AGENT_TRACE == "db"


def test_mode_raw_settings_valid(monkeypatch, clean_settings_cache) -> None:
    """En mode raw, les settings restent valides."""
    monkeypatch.setenv("LLM_AGENT_MODE", "raw")
    from app.config import get_settings as _gs
    _gs.cache_clear()
    s = _gs()
    assert s.LLM_AGENT_MODE == "raw"


def test_mode_invalid_rejected(monkeypatch, clean_settings_cache) -> None:
    """Une valeur autre que langgraph|raw doit être rejetée."""
    from pydantic import ValidationError

    monkeypatch.setenv("LLM_AGENT_MODE", "bogus")
    from app.config import get_settings as _gs
    _gs.cache_clear()
    with pytest.raises(ValidationError):
        _gs()
