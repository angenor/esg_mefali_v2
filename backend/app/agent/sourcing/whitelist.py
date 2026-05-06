"""F56 / FR-014 — Whitelist de patterns "non factuels".

Ces patterns matchent des tournures pédagogiques, conditionnelles, ou
généralisantes — qui ne devraient pas déclencher un retry sourçage.

Politique : si une phrase **matche** un pattern, le détecteur écarte la
phrase entière (aucun claim n'est extrait à l'intérieur de cette phrase).

Volontairement conservateur : ≥ 20 patterns initiaux ; à enrichir via le
golden set (FR-015) ; tests dans ``tests/unit/test_sourcing_whitelist.py``.
"""

from __future__ import annotations

import re

# Patterns regex insensitives à la casse. Compilés au chargement du module
# pour éviter le coût de compilation à chaque appel.
WHITELIST_PATTERNS: tuple[re.Pattern[str], ...] = (
    # Adverbes / locutions généralisantes
    re.compile(r"\bEn g[ée]n[ée]ral\b", re.IGNORECASE),
    re.compile(r"\bG[ée]n[ée]ralement\b", re.IGNORECASE),
    re.compile(r"\bGlobalement\b", re.IGNORECASE),
    re.compile(r"\bTypiquement\b", re.IGNORECASE),
    re.compile(r"\bHabituellement\b", re.IGNORECASE),
    re.compile(r"\bSouvent\b", re.IGNORECASE),
    re.compile(r"\bParfois\b", re.IGNORECASE),
    re.compile(r"\bDans la plupart des cas\b", re.IGNORECASE),
    re.compile(r"\bLa plupart du temps\b", re.IGNORECASE),
    # Conditionnels / dépendances
    re.compile(r"\bCela d[ée]pend\b", re.IGNORECASE),
    re.compile(r"\b[ÇC]a d[ée]pend\b", re.IGNORECASE),
    re.compile(r"\bSelon le cas\b", re.IGNORECASE),
    re.compile(r"\bSi vous (avez|voulez|souhaitez)\b", re.IGNORECASE),
    re.compile(r"\bCela peut varier\b", re.IGNORECASE),
    # Pédagogique / hypothétique
    re.compile(r"\bImaginons que\b", re.IGNORECASE),
    re.compile(r"\bSupposons que\b", re.IGNORECASE),
    re.compile(r"\bPrenons l'exemple\b", re.IGNORECASE),
    # Marqueurs d'opinion
    re.compile(r"\b[ÀA] mon avis\b", re.IGNORECASE),
    re.compile(r"\bSelon moi\b", re.IGNORECASE),
    # Théoriques / mod[é]ratifs
    re.compile(r"\bEn th[ée]orie\b", re.IGNORECASE),
    re.compile(r"\bIl est (g[ée]n[ée]ralement )?admis\b", re.IGNORECASE),
    re.compile(r"\bBien entendu\b", re.IGNORECASE),
    # Ouvertures de listes / suggestions
    re.compile(r"\bOn peut (consid[ée]rer|envisager)\b", re.IGNORECASE),
    re.compile(r"\bVous pouvez (explorer|envisager|consid[ée]rer)\b", re.IGNORECASE),
    re.compile(r"\b(Les |des )?PME en g[ée]n[ée]ral\b", re.IGNORECASE),
    re.compile(r"\bGlobalement parlant\b", re.IGNORECASE),
)


def is_whitelisted(sentence: str) -> bool:
    """Retourne ``True`` si l'un des patterns whitelist matche ``sentence``.

    La fonction est utilisée par le détecteur sur chaque "phrase" délimitée
    par ``.``, ``?``, ``!``. La détection est case-insensitive.
    """
    if not sentence or not sentence.strip():
        return False
    for pat in WHITELIST_PATTERNS:
        if pat.search(sentence):
            return True
    return False


__all__ = ["WHITELIST_PATTERNS", "is_whitelisted"]
