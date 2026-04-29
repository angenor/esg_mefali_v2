"""Client embeddings — Voyage AI (modèle ``voyage-3.5``, dimension 1024).

**F01** : fonction posée et testable, mais aucun appel exécuté en production.
**F18** : usage effectif (RAG / mémoire LLM) sur ``chat_message.embedding``.

Pourquoi ce module et pas le SDK ``voyageai`` :
au moment de F01, le SDK officiel ``voyageai`` ne supporte pas Python 3.14.
Un appel ``httpx`` direct sur l'API Voyage couvre 100 % du besoin de F18
(``POST /v1/embeddings``).
"""

from __future__ import annotations

import os

import httpx

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_MODEL = "voyage-3.5"
VOYAGE_DIM = 1024
DEFAULT_TIMEOUT_SECONDS = 30.0


class VoyageError(RuntimeError):
    """Erreur générique d'appel à l'API Voyage."""


def embed(texts: list[str], *, timeout: float = DEFAULT_TIMEOUT_SECONDS) -> list[list[float]]:
    """Renvoie la liste d'embeddings pour ``texts``.

    Args:
        texts: liste non vide de chaînes à embedder.
        timeout: timeout HTTP (secondes).

    Returns:
        Liste d'embeddings (chaque embedding = liste de ``VOYAGE_DIM`` floats).

    Raises:
        ValueError: si ``texts`` est vide.
        RuntimeError: si la variable ``VOYAGE_API_KEY`` est absente
            (message contient explicitement ``VOYAGE_API_KEY``).
        VoyageError: en cas d'erreur HTTP côté Voyage.
    """
    if not texts:
        raise ValueError("texts must be a non-empty list")

    api_key = os.environ.get("VOYAGE_API_KEY")
    if not api_key:
        raise RuntimeError(
            "VOYAGE_API_KEY missing — exporter la variable ou la définir dans .env"
        )

    payload = {"input": texts, "model": VOYAGE_MODEL}
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        response = httpx.post(
            VOYAGE_API_URL, json=payload, headers=headers, timeout=timeout
        )
    except httpx.HTTPError as exc:
        raise VoyageError(f"Voyage HTTP error: {exc}") from exc

    if response.status_code != 200:
        raise VoyageError(
            f"Voyage API returned {response.status_code}: {response.text[:200]}"
        )

    data = response.json()
    return [item["embedding"] for item in data.get("data", [])]
