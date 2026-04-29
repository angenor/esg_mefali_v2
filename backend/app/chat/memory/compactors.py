"""F18 — Compacteurs purs (profil entreprise, projets, tokens, budget).

Toutes les fonctions de ce module sont pures (pas d'I/O) et déterministes.
Elles transforment les payloads bruts F11/F12 en représentations compactes
safes pour le LLM, et appliquent la stratégie de compaction sous budget
tokens (R4 du research.md).

Invariants :

- Whitelist explicite (deny-by-default) sur ``PROFILE_ALLOWED_KEYS`` et
  ``PROJECT_ALLOWED_KEYS``.
- Money typé conservé tel quel (``{amount, currency}``) sans cast float.
- Troncature de description bornée par ``DEFAULT_DESC_LIMIT`` puis dégradée
  100 → 50 si le budget tokens force.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from typing import Any

# --- Whitelist profil entreprise (FR-002, FR-014) ---
PROFILE_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "raison_sociale",
        "forme_juridique",
        "secteur_activite",
        "pays",
        "ville",
        "effectif_total",
        "chiffre_affaires",
        "annee_creation",
        "description_activite",
        "indicateurs_esg_synthetiques",
    }
)

# --- Whitelist projet (FR-003) ---
PROJECT_ALLOWED_KEYS: frozenset[str] = frozenset(
    {
        "id",
        "nom",
        "statut",
        "secteur",
        "pays",
        "montant_total",
        "description",
        "date_debut",
        "date_fin_prevue",
    }
)

# Statuts considérés inactifs — exclus de la liste compactée.
PROJECT_ACTIVE_DENYLIST: frozenset[str] = frozenset({"cloture", "annule", "rejete"})

DEFAULT_DESC_LIMIT: int = 200
DEFAULT_MAX_PROJECTS: int = 10
MIN_RECENT_MESSAGES: int = 5  # plancher de la passe 3 de fit_to_budget


def _truncate(text: str | None, limit: int) -> str | None:
    """Tronque ``text`` à ``limit`` caractères, ajoute une ellipse si coupé."""
    if text is None:
        return None
    if not isinstance(text, str):
        text = str(text)
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def compact_profile(
    entreprise: dict[str, Any] | None,
    *,
    desc_limit: int = DEFAULT_DESC_LIMIT,
) -> dict[str, Any] | None:
    """Compacte un profil entreprise via la whitelist FR-002.

    Args:
        entreprise: dict brut issu du repository F11 (ou None si absent).
        desc_limit: limite de troncature pour ``description_activite``.

    Returns:
        Dict ne contenant que les clés whitelisted et non vides, ou ``None``
        si le profil est totalement vide après filtrage.
    """
    if not entreprise:
        return None

    out: dict[str, Any] = {}
    for key in PROFILE_ALLOWED_KEYS:
        if key not in entreprise:
            continue
        value = entreprise[key]
        if value is None or value == "" or value == [] or value == {}:
            continue
        if key == "description_activite" and isinstance(value, str):
            value = _truncate(value, desc_limit)
        out[key] = value

    return out or None


def compact_projets(
    projets: Iterable[dict[str, Any]] | None,
    *,
    max_n: int = DEFAULT_MAX_PROJECTS,
    desc_limit: int = DEFAULT_DESC_LIMIT,
) -> list[dict[str, Any]]:
    """Filtre les projets actifs et compacte chaque entrée (whitelist FR-003).

    Args:
        projets: itérable de dicts projets (issus du repository F12).
        max_n: nombre max de projets retenus.
        desc_limit: limite de troncature pour ``description``.

    Returns:
        Liste de projets compactés (longueur <= ``max_n``). Vide si pas de
        projet actif.
    """
    if not projets:
        return []

    out: list[dict[str, Any]] = []
    for projet in projets:
        if not projet:
            continue
        statut = projet.get("statut")
        if isinstance(statut, str) and statut.lower() in PROJECT_ACTIVE_DENYLIST:
            continue
        compact: dict[str, Any] = {}
        for key in PROJECT_ALLOWED_KEYS:
            if key not in projet:
                continue
            value = projet[key]
            if value is None or value == "" or value == [] or value == {}:
                continue
            if key == "description" and isinstance(value, str):
                value = _truncate(value, desc_limit)
            compact[key] = value
        if compact:
            out.append(compact)
        if len(out) >= max_n:
            break

    return out


def extract_embedding_text(content: str, payload_json: dict[str, Any] | None) -> str:
    """Retourne le texte pertinent à embedder pour un message (FR-008).

    Pour les messages tool (visualisation, action), on préfère le label/title
    humain plutôt que le JSON brut qui pollue la similarité sémantique.

    Args:
        content: texte du message (peut être vide pour les payloads purs).
        payload_json: payload tool éventuel.

    Returns:
        Texte non-vide à embedder. Fallback : ``content``.
    """
    base = (content or "").strip()
    if payload_json and isinstance(payload_json, dict):
        for key in ("label", "title", "summary", "name"):
            value = payload_json.get(key)
            if isinstance(value, str) and value.strip():
                desc = payload_json.get("description")
                if isinstance(desc, str) and desc.strip():
                    return f"{value.strip()} — {desc.strip()}"
                return value.strip()
    return base


def estimate_tokens(text: str) -> int:
    """Approxime le nombre de tokens d'un texte (R3 — ``len // 4``)."""
    if not text:
        return 0
    return max(1, len(text) // 4)


def fit_to_budget(
    *,
    profile: dict[str, Any] | None,
    projets: list[dict[str, Any]],
    messages: list[dict[str, Any]],
    render: Callable[
        [dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]], str
    ],
    budget: int,
) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]], int]:
    """Réduit déterministiquement le bundle jusqu'à passer sous le budget.

    Stratégie R4 (3 passes) :

    1. Tronquer toutes les descriptions projet : 200 → 100 → 50.
    2. Réduire le nombre de projets : 10 → 7 → 5 → 3 → 0.
    3. Raccourcir la fenêtre messages : len → 12 → 10 → 8 → 5 (plancher).

    Args:
        profile: dict profil compact (peut être None).
        projets: liste projets compacts.
        messages: liste messages bruts (ordre chronologique).
        render: fonction ``(profile, projets, messages) -> str`` produisant
            le markdown final dont on mesure la taille.
        budget: budget tokens cible.

    Returns:
        Tuple ``(profile, projets, messages, estimated_tokens)``. Si le
        plancher minimal dépasse encore le budget, on retourne tel quel.
    """
    cur_projets = list(projets)
    cur_messages = list(messages)

    def _render_size() -> int:
        return estimate_tokens(render(profile, cur_projets, cur_messages))

    if _render_size() <= budget:
        return profile, cur_projets, cur_messages, _render_size()

    # Passe 1 — descriptions projets
    for desc_limit in (100, 50):
        cur_projets = [
            {**p, "description": _truncate(p.get("description"), desc_limit)}
            if isinstance(p.get("description"), str)
            else p
            for p in cur_projets
        ]
        if _render_size() <= budget:
            return profile, cur_projets, cur_messages, _render_size()

    # Passe 2 — nombre de projets
    for projets_cap in (7, 5, 3, 0):
        cur_projets = cur_projets[:projets_cap]
        if _render_size() <= budget:
            return profile, cur_projets, cur_messages, _render_size()

    # Passe 3 — fenêtre messages (plancher MIN_RECENT_MESSAGES)
    for messages_cap in (12, 10, 8, MIN_RECENT_MESSAGES):
        if len(cur_messages) > messages_cap:
            cur_messages = cur_messages[-messages_cap:]
        if _render_size() <= budget:
            return profile, cur_projets, cur_messages, _render_size()

    return profile, cur_projets, cur_messages, _render_size()
