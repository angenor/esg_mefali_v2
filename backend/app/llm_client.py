"""Client LLM centralisé (OpenRouter via SDK ``openai``).

**F01** : factory posée mais aucun appel exécuté.
**F14+** : utilisation effective dans les agents LangGraph.

Exemple d'usage (post-F14) ::

    from app.llm_client import get_llm_client

    client = get_llm_client()
    completion = client.chat.completions.create(
        model=get_settings().LLM_MODEL,
        messages=[{"role": "user", "content": "ping"}],
    )
"""

from __future__ import annotations

from functools import lru_cache

from openai import OpenAI

from app.config import get_settings


@lru_cache(maxsize=1)
def get_llm_client() -> OpenAI:
    """Retourne un client OpenAI configuré pour OpenRouter (ou compatible).

    La factory est mémoïsée — un seul client réutilisé pour toute l'app.
    """
    settings = get_settings()
    return OpenAI(
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        default_headers={"HTTP-Referer": settings.APP_URL},
    )
