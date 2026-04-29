"""F07 — HEAD probe non bloquant pour valider qu'une URL répond (FR-007).

Contrat :
- timeout 5s par défaut, suit les redirections HTTP.
- ne lève **jamais** : la fonction renvoie toujours ``{ok, status, error}``.
- ``ok`` = True si statut 2xx ; False sinon (404, erreur, timeout).

Le probe est appelé en best-effort lors de la création/mise à jour d'une
source ; un échec n'empêche pas la persistance — il alimente seulement
``head_warning`` dans la réponse.
"""

from __future__ import annotations

from typing import TypedDict

import httpx

DEFAULT_TIMEOUT_SECONDS = 5.0


class ProbeResult(TypedDict):
    ok: bool
    status: int | None
    error: str | None


async def probe_url(
    url: str,
    *,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    transport: httpx.AsyncBaseTransport | None = None,
) -> ProbeResult:
    """Lance un HEAD sur ``url`` (avec fallback GET si HEAD interdit).

    Args:
        url: URL absolue (https recommandé).
        timeout: timeout total (s).
        transport: transport injecté (utilisé par les tests via
            ``httpx.MockTransport``).
    """
    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            transport=transport,
        ) as client:
            try:
                resp = await client.head(url)
            except httpx.HTTPError:
                # Fallback GET — certains serveurs bloquent HEAD.
                resp = await client.get(url)
            status = int(resp.status_code)
            return {
                "ok": 200 <= status < 300,
                "status": status,
                "error": None,
            }
    except (httpx.TimeoutException, httpx.ConnectTimeout, httpx.ReadTimeout):
        return {"ok": False, "status": None, "error": "timeout"}
    except httpx.HTTPError:
        return {"ok": False, "status": None, "error": "network"}
    except Exception:  # noqa: BLE001 — best-effort, jamais bloquant
        return {"ok": False, "status": None, "error": "unknown"}


__all__ = ["probe_url", "ProbeResult", "DEFAULT_TIMEOUT_SECONDS"]
