"""F23 — Mapping ``indicateur.code`` → valeur PME (lecture seule).

MVP : dictionnaire en code, lit principalement depuis ``EntrepriseRow`` (F11).
Pas de migration F09 (pas de colonne ``value_source_path`` en base).

Ajouter un indicateur supporté = ajouter une entrée dans ``VALUE_SOURCE_MAP``.
Si l'indicateur n'est pas dans le map → l'engine signale ``value_source_unmapped``.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


def _safe_get(obj: Any, attr: str) -> Any:
    """Lit un attribut sur un objet (dataclass) ou une clé de dict."""
    if obj is None:
        return None
    if isinstance(obj, dict):
        return obj.get(attr)
    return getattr(obj, attr, None)


def _from_jsonb(field: str, key: str) -> Callable[[Any], Any]:
    """Sondage d'un sous-champ JSONB ``entreprise.<field>[<key>]``."""

    def _get(entreprise: Any) -> Any:
        blob = _safe_get(entreprise, field)
        if blob is None:
            return None
        if isinstance(blob, dict):
            return blob.get(key)
        return None

    return _get


def _direct(attr: str) -> Callable[[Any], Any]:
    def _get(entreprise: Any) -> Any:
        return _safe_get(entreprise, attr)

    return _get


# Mapping minimal MVP ; extensible sans migration.
VALUE_SOURCE_MAP: dict[str, Callable[[Any], Any]] = {
    "EFFECTIFS_TOTAL": _direct("taille_effectifs"),
    "DEMO_S1": _direct("taille_effectifs"),
    "CA_AMOUNT": _direct("taille_ca_amount"),
    "DEMO_E1": _direct("taille_ca_amount"),
    "PAYS_SIEGE": _direct("localisation_siege_pays_iso2"),
    "GOUVERNANCE_BOARD_INDEPENDENCE": _from_jsonb("gouvernance_json", "board_independence"),
    "GOUVERNANCE_AUDIT_INTERNE": _from_jsonb("gouvernance_json", "audit_interne"),
    "PRATIQUE_POLITIQUE_RSE": _from_jsonb("pratiques_actuelles_json", "politique_rse"),
    "PRATIQUE_BILAN_CARBONE": _from_jsonb("pratiques_actuelles_json", "bilan_carbone"),
    "DEMO_G1": _from_jsonb("gouvernance_json", "audit_interne"),
}


def resolve_value(*, indicateur_code: str, entreprise: Any) -> tuple[Any, str | None]:
    """Résout la valeur PME pour un code d'indicateur.

    Returns:
        ``(valeur, None)`` si lookup OK (la valeur peut être ``None`` →
        l'engine remontera ``value_absent``).
        ``(None, "value_source_unmapped")`` si pas de mapping.
    """
    fn = VALUE_SOURCE_MAP.get(indicateur_code)
    if fn is None:
        return (None, "value_source_unmapped")
    return (fn(entreprise), None)


def collect_values(
    *,
    indicateur_codes: list[str],
    entreprise: Any,
) -> tuple[dict[str, Any], dict[str, str]]:
    """Résout en lot toutes les valeurs ; sépare les codes mappés des non-mappés.

    Returns:
        ``(values, unmapped)`` où ``values`` est ``code -> valeur`` (None
        possible si la PME n'a pas renseigné), et ``unmapped`` est
        ``code -> reason`` pour les codes non mappés.
    """
    values: dict[str, Any] = {}
    unmapped: dict[str, str] = {}
    for code in indicateur_codes:
        v, reason = resolve_value(indicateur_code=code, entreprise=entreprise)
        if reason is not None:
            unmapped[code] = reason
        else:
            values[code] = v
    return values, unmapped
