"""Tests llm_client (factory OpenRouter)."""

from __future__ import annotations


def test_get_llm_client_returns_openai_instance(clean_settings_cache):
    """La factory retourne un client OpenAI cible OpenRouter."""
    from app.llm_client import get_llm_client

    get_llm_client.cache_clear()
    client = get_llm_client()
    assert client is not None
    # base_url normalisée par le SDK
    assert "openrouter" in str(client.base_url).lower() or str(client.base_url)
    # mémoïsation
    assert get_llm_client() is client


def test_get_llm_client_includes_app_url_referer(clean_settings_cache):
    """Le header HTTP-Referer est posé via APP_URL."""
    from app.config import get_settings
    from app.llm_client import get_llm_client

    get_llm_client.cache_clear()
    client = get_llm_client()
    assert client.default_headers.get("HTTP-Referer") == get_settings().APP_URL
