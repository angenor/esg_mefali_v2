"""F23 — Normalisation des valeurs PME en score 0-100.

Règles (cf. specs/023-.../research.md D2) :
- ``numeric`` avec seuils → linéaire bornée ``(v - min)/(max - min) * 100``.
- ``numeric`` sans seuils → clamp(v, 0, 100).
- ``boolean`` → 100 si vrai, 0 sinon.
- ``enum`` ordonnée → ``index/(len-1) * 100``.
- ``text`` / ``json`` → non supporté MVP.
"""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any


@dataclass(frozen=True)
class NormalizeResult:
    """Résultat d'une normalisation : soit valeur, soit reason de manquant."""

    value: float | None
    reason: str | None  # None ⇔ couvert ; sinon code d'exclusion

    @property
    def is_covered(self) -> bool:
        return self.value is not None and self.reason is None


def _to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, bool):
        return 1.0 if value else 0.0
    if isinstance(value, (int, float, Decimal)):
        return float(value)
    return None


def _clamp(v: float, low: float = 0.0, high: float = 100.0) -> float:
    return max(low, min(high, v))


def normalize_value(  # noqa: PLR0911 — branches pédagogiques
    *,
    value: Any,
    value_type: str,
    seuil_min: Any = None,
    seuil_max: Any = None,
    enum_values: list[Any] | None = None,
) -> NormalizeResult:
    """Convertit une valeur PME en score 0-100 selon le ``value_type``."""
    if value is None:
        return NormalizeResult(value=None, reason="value_absent")

    vt = (value_type or "").lower()

    if vt == "boolean":
        if isinstance(value, bool):
            return NormalizeResult(value=100.0 if value else 0.0, reason=None)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return NormalizeResult(
                value=100.0 if float(value) != 0.0 else 0.0, reason=None
            )
        if isinstance(value, str):
            low = value.strip().lower()
            if low in {"true", "1", "yes", "oui"}:
                return NormalizeResult(value=100.0, reason=None)
            if low in {"false", "0", "no", "non"}:
                return NormalizeResult(value=0.0, reason=None)
        return NormalizeResult(value=None, reason="invalid_value")

    if vt == "enum":
        if not enum_values or len(enum_values) == 0:
            return NormalizeResult(
                value=None, reason="referentiel_indicateur_misconfig"
            )
        try:
            idx = list(enum_values).index(value)
        except ValueError:
            return NormalizeResult(value=None, reason="invalid_value")
        if len(enum_values) == 1:
            return NormalizeResult(value=100.0, reason=None)
        return NormalizeResult(
            value=round(idx / (len(enum_values) - 1) * 100.0, 4),
            reason=None,
        )

    if vt == "numeric":
        v = _to_float(value)
        if v is None:
            return NormalizeResult(value=None, reason="invalid_value")
        smin = _to_float(seuil_min)
        smax = _to_float(seuil_max)
        if smin is not None and smax is not None:
            if smax <= smin:
                return NormalizeResult(
                    value=None, reason="referentiel_indicateur_misconfig"
                )
            normalized = (v - smin) / (smax - smin) * 100.0
            return NormalizeResult(value=_clamp(normalized), reason=None)
        return NormalizeResult(value=_clamp(v), reason=None)

    return NormalizeResult(value=None, reason="unsupported_value_type")
