"""F58 — Détection de langue + politique de retry FR (FR-005, FR-006).

Utilise ``langdetect`` (lib légère, ~5 ms par appel). Fallback ``unknown``
si :
- texte trop court (< 30 chars utiles) ;
- détection lève une exception (texte non latin, vide).
"""

from __future__ import annotations

import logging
from typing import Final

logger = logging.getLogger(__name__)

# Langues reconnues côté politique. Wolof/Bambara post-MVP.
_KNOWN_LANGS: Final[frozenset[str]] = frozenset({"fr", "en", "es", "ar"})
_RETRY_TARGET_LANGS: Final[frozenset[str]] = frozenset({"en", "es", "ar"})

_MIN_TEXT_LEN: Final[int] = 30


def detect_language(text: str) -> str:
    """Retourne ISO 639-1 (``fr``, ``en``, ``es``, ``ar``) ou ``unknown``.

    Comportement défensif :
    - texte vide/court → ``unknown`` (évite faux positifs).
    - exception langdetect → ``unknown`` + log debug (jamais bloquant).
    - langue détectée hors ``_KNOWN_LANGS`` → garde le code détecté tel quel
      (le caller décide).
    """
    if not text or len(text.strip()) < _MIN_TEXT_LEN:
        return "unknown"
    try:
        # Import paresseux : langdetect est lent à charger.
        from langdetect import DetectorFactory, detect

        # Determinisme entre runs (FR-005 reproductibilité tests).
        DetectorFactory.seed = 0
        return detect(text)
    except Exception:  # noqa: BLE001 - never break flow
        logger.debug("detect_language failed (returning 'unknown')", exc_info=True)
        return "unknown"


def needs_french_retry(
    detected_lang: str,
    user_lang_pref: str,
    offer_accepted_langs: list[str] | None,
) -> bool:
    """Décide si un retry FR doit être déclenché (FR-006).

    True ssi :
    - ``user_lang_pref == 'fr'`` ;
    - ``detected_lang ∈ {en, es, ar}`` (politique de dérive) ;
    - ``offer_accepted_langs`` ne contient PAS ``detected_lang`` (sinon la
      politique de l'offre prime sur la préférence utilisateur).

    False sinon (notamment ``detected_lang == 'unknown'``).
    """
    if user_lang_pref != "fr":
        return False
    if detected_lang not in _RETRY_TARGET_LANGS:
        return False
    if offer_accepted_langs and detected_lang in offer_accepted_langs:
        return False
    return True


__all__ = ["detect_language", "needs_french_retry"]
