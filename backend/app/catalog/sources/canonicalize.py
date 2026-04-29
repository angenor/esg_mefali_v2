"""F07 — Canonicalisation d'URL pour la table ``source``.

Règles (Q1 spec) :
- forcer https
- lower-case host
- retrait du préfixe "www."
- retrait du slash final (sauf si la racine "/")
- retrait des params utm_*, fbclid, gclid, mc_cid, mc_eid
- conservation du fragment (#...)
- idempotente

Implémentation : ``urllib.parse``, sans dépendance externe.
"""

from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

# Paramètres de query supprimés. Les params préfixés `utm_` sont retirés par règle.
_TRACKING_PARAMS_EXACT: frozenset[str] = frozenset(
    {"fbclid", "gclid", "mc_cid", "mc_eid"}
)


def _is_tracking_param(name: str) -> bool:
    n = name.lower()
    return n.startswith("utm_") or n in _TRACKING_PARAMS_EXACT


def canonicalize_url(raw: str) -> str:
    """Renvoie la forme canonique de ``raw``.

    Lève ``ValueError`` si l'URL est invalide (vide, sans scheme http(s),
    sans host).
    """
    if not isinstance(raw, str):  # type: ignore[unreachable]
        raise ValueError("URL must be a string")

    url = raw.strip()
    if not url:
        raise ValueError("URL is empty")

    parts = urlsplit(url)

    # Scheme : on accepte http/https et on force https.
    scheme = (parts.scheme or "").lower()
    if scheme not in ("http", "https"):
        raise ValueError(f"Unsupported scheme: {scheme!r}")
    new_scheme = "https"

    # Host : lower-case, retrait du préfixe www. (mais pas www.* multi-niveaux).
    host = (parts.hostname or "").lower()
    if not host:
        raise ValueError("URL is missing host")
    if host.startswith("www."):
        host = host[4:]

    # Conserve le port s'il est présent.
    netloc = host
    if parts.port is not None:
        # On ne reconstruit pas userinfo (pas pertinent pour des sources publiques).
        netloc = f"{host}:{parts.port}"

    # Path : retrait du slash final sauf si racine.
    path = parts.path or ""
    if path == "":
        path = "/"
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/")
        if path == "":
            path = "/"

    # Si la racine "/" et qu'il n'y a ni query ni fragment, on conserve "/".
    # Sinon (sous-chemin) on a déjà retiré le slash final.

    # Query : retire les params de tracking (utm_*, fbclid, gclid, mc_cid, mc_eid).
    # ``parse_qsl(keep_blank_values=True)`` préserve l'ordre des params.
    query_pairs = [
        (k, v)
        for k, v in parse_qsl(parts.query, keep_blank_values=True)
        if not _is_tracking_param(k)
    ]
    new_query = urlencode(query_pairs, doseq=True)

    # Fragment : conservé tel quel.
    fragment = parts.fragment

    # Cas spécial racine sans query/fragment : conserver le "/" final.
    if path == "/" and not new_query and not fragment:
        return urlunsplit((new_scheme, netloc, "/", "", ""))

    # Pour un sous-chemin sans query/fragment, on n'ajoute pas de "/" final.
    return urlunsplit((new_scheme, netloc, path, new_query, fragment))


__all__ = ["canonicalize_url"]
