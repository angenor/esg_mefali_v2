"""Client embeddings — Voyage AI (modèle ``voyage-3.5``, dimension 1024).

**F01** : fonction posée et testable, mais aucun appel exécuté en production.
**F18** : usage effectif (RAG / mémoire LLM) sur ``chat_message.embedding``.
**F57** : guards de dimension + helper ``hash_query`` (cache embedding US8 +
recall_log query_hash US9 — privacy-friendly, pas la query brute).

Pourquoi ce module et pas le SDK ``voyageai`` :
au moment de F01, le SDK officiel ``voyageai`` ne supporte pas Python 3.14.
Un appel ``httpx`` direct sur l'API Voyage couvre 100 % du besoin de F18
(``POST /v1/embeddings``).
"""

from __future__ import annotations

import hashlib
import os

import httpx

VOYAGE_API_URL = "https://api.voyageai.com/v1/embeddings"
VOYAGE_MODEL = "voyage-3.5"
VOYAGE_DIM = 1024
DEFAULT_TIMEOUT_SECONDS = 30.0


class VoyageError(RuntimeError):
    """Erreur générique d'appel à l'API Voyage."""


class VoyageDimMismatchError(VoyageError):
    """Erreur fatale : la dimension renvoyée par Voyage ≠ ``VOYAGE_DIM``.

    F57 / FR-016 — un mismatch dim révèle une corruption de config (modèle
    Voyage changé) qui rendrait pgvector incompatible avec la colonne
    ``vector(1024)``. On lève fail-fast plutôt que d'écrire des embeddings
    incohérents.
    """


def hash_query(query: str) -> str:
    """Calcule le SHA-256 hex d'une query — utilisé par cache embedding (US8)
    et par ``recall_log.query_hash`` (US9, privacy-friendly).

    On normalise volontairement (strip + lower) pour que des queries
    sémantiquement identiques partagent le même cache slot.
    """
    normalized = (query or "").strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _check_dim(vec: list[float]) -> list[float]:
    """Garde-fou F57 : refuse un embedding de dimension inattendue."""
    if len(vec) != VOYAGE_DIM:
        raise VoyageDimMismatchError(
            f"Voyage returned embedding of dim {len(vec)} ; expected {VOYAGE_DIM}"
        )
    return vec


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
        VoyageDimMismatchError: si Voyage renvoie une dim ≠ 1024 (F57 FR-016).
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
    return [_check_dim(list(item["embedding"])) for item in data.get("data", [])]


__all__ = [
    "DEFAULT_TIMEOUT_SECONDS",
    "VOYAGE_API_URL",
    "VOYAGE_DIM",
    "VOYAGE_MODEL",
    "VoyageDimMismatchError",
    "VoyageError",
    "embed",
    "hash_query",
]
