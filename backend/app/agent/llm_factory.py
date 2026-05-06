"""F53 / T013 — Factory ChatOpenAI configuré depuis ``Settings``.

Ne JAMAIS hard-coder l'URL/clé/modèle (NFR-007). Utilise toujours
``LLM_BASE_URL``, ``LLM_API_KEY``, ``LLM_MODEL`` issus de la config.
"""

from __future__ import annotations

from typing import Any

from langchain_openai import ChatOpenAI

from app.config import Settings, get_settings


def build_chat_model(settings: Settings | None = None, **overrides: Any) -> ChatOpenAI:
    """Retourne un ``ChatOpenAI`` configuré pour OpenRouter.

    Streaming activé par défaut (FR-005). ``timeout`` correspond à
    ``LLM_AGENT_TIMEOUT_S`` afin que le runner puisse interrompre proprement
    un nœud LLM trop long.
    """
    s = settings or get_settings()
    kwargs: dict[str, Any] = {
        "model": s.LLM_MODEL,
        "base_url": s.LLM_BASE_URL,
        "api_key": s.LLM_API_KEY,
        "streaming": True,
        "timeout": s.LLM_AGENT_TIMEOUT_S,
        "max_retries": 0,  # le retry est géré explicitement par le validator
    }
    kwargs.update(overrides)
    return ChatOpenAI(**kwargs)


__all__ = ["build_chat_model"]
