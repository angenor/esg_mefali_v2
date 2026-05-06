"""F58 — PII regex catalog (FR-003).

Patterns are kept as a constant module to separate data from logic. Adding
a new format only requires extending :data:`DEFAULT_PII_PATTERNS`.

Coverage in MVP:
- Mobile money UEMOA: CI (+225), SN (+221), BJ (+229), TG (+228), BF (+226).
- CNI / passeport UEMOA (heuristic).
- IBAN (FR / SN / generic 22-34 chars).
- Carte bancaire 13–19 digits with Luhn validation.

False positives on common business numbers (« 07 employés », « facteur 2.6 »)
are avoided by:
- requiring the international prefix (``+225``) OR a 10-digit local block,
- card numbers only masked when Luhn-valid.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final, Literal

PiiName = Literal[
    "mobile_money_ci",
    "mobile_money_sn",
    "mobile_money_bj",
    "mobile_money_tg",
    "mobile_money_bf",
    "cni_uemoa",
    "iban",
    "card_luhn",
]


@dataclass(frozen=True)
class PiiPattern:
    """Définition d'un pattern PII."""

    name: PiiName
    regex: re.Pattern[str]
    mask_template: str
    requires_luhn_check: bool = False


# ---------------------------------------------------------------------------
# Mobile money UEMOA — formats acceptés
# ---------------------------------------------------------------------------
# International form (+22X) avec espaces ou non. Local form (10 chiffres
# commençant par 0). Pour limiter les faux positifs sur "07 employés", on
# exige soit l'indicatif +22X explicite, soit 10 chiffres consécutifs
# (avec espaces optionnels) précédés de tel/whatsapp/contact, ou en
# présence d'au moins 8 chiffres groupés.

_MOBILE_FORMAT = (
    r"(?:\+225|\+221|\+229|\+228|\+226)\s?\d(?:[\s.-]?\d){7,9}"  # international
)

_MOBILE_LOCAL_10D = (
    r"(?<!\d)0\d(?:[\s.-]?\d){8}(?!\d)"  # 10-digit local (more strict)
)

_MOBILE_PATTERNS: Final[tuple[PiiPattern, ...]] = (
    PiiPattern(
        name="mobile_money_ci",
        regex=re.compile(r"\+225\s?\d(?:[\s.-]?\d){7,9}"),
        mask_template="+225 ** ** ** ** **",
    ),
    PiiPattern(
        name="mobile_money_sn",
        regex=re.compile(r"\+221\s?\d(?:[\s.-]?\d){7,9}"),
        mask_template="+221 ** ** ** ** **",
    ),
    PiiPattern(
        name="mobile_money_bj",
        regex=re.compile(r"\+229\s?\d(?:[\s.-]?\d){7,9}"),
        mask_template="+229 ** ** ** ** **",
    ),
    PiiPattern(
        name="mobile_money_tg",
        regex=re.compile(r"\+228\s?\d(?:[\s.-]?\d){7,9}"),
        mask_template="+228 ** ** ** ** **",
    ),
    PiiPattern(
        name="mobile_money_bf",
        regex=re.compile(r"\+226\s?\d(?:[\s.-]?\d){7,9}"),
        mask_template="+226 ** ** ** ** **",
    ),
    # Local 10-digit form (must be 10 digits — eliminates "07 employés")
    PiiPattern(
        name="mobile_money_ci",
        regex=re.compile(_MOBILE_LOCAL_10D),
        mask_template="** ** ** ** **",
    ),
)

# ---------------------------------------------------------------------------
# CNI / passeport UEMOA (heuristique : préfixe 2 lettres + 10 chiffres)
# ---------------------------------------------------------------------------

_CNI_PATTERN: Final[PiiPattern] = PiiPattern(
    name="cni_uemoa",
    regex=re.compile(r"\b[A-Z]{2}\d{8,12}\b"),
    mask_template="**********",
)

# ---------------------------------------------------------------------------
# IBAN (4 lettres + 2 chiffres + 11–30 alphanum, regroupés par 4 souvent)
# ---------------------------------------------------------------------------

_IBAN_PATTERN: Final[PiiPattern] = PiiPattern(
    name="iban",
    regex=re.compile(
        r"\b[A-Z]{2}\d{2}(?:\s?[A-Z0-9]{4}){3,8}(?:\s?[A-Z0-9]{1,4})?\b"
    ),
    mask_template="**** **** **** **** ****",
)

# ---------------------------------------------------------------------------
# Carte bancaire (13–19 chiffres groupés ou non) — vérification Luhn obligatoire
# ---------------------------------------------------------------------------

_CARD_PATTERN: Final[PiiPattern] = PiiPattern(
    name="card_luhn",
    regex=re.compile(r"\b(?:\d[ -]?){12,18}\d\b"),
    mask_template="**** **** **** ****",
    requires_luhn_check=True,
)


DEFAULT_PII_PATTERNS: Final[tuple[PiiPattern, ...]] = (
    *_MOBILE_PATTERNS,
    _IBAN_PATTERN,  # IBAN AVANT carte (overlap possible)
    _CARD_PATTERN,
    _CNI_PATTERN,
)


# ---------------------------------------------------------------------------
# Luhn check
# ---------------------------------------------------------------------------


def luhn_valid(digits: str) -> bool:
    """Vérifie qu'une chaîne de 13–19 chiffres satisfait l'algorithme de Luhn.

    Renvoie False si la chaîne contient autre chose que des chiffres ou est
    de longueur invalide.
    """
    s = digits.replace(" ", "").replace("-", "")
    if not s.isdigit() or not (13 <= len(s) <= 19):
        return False
    total = 0
    parity = len(s) % 2
    for i, ch in enumerate(s):
        d = int(ch)
        if i % 2 == parity:
            d *= 2
            if d > 9:
                d -= 9
        total += d
    return total % 10 == 0


__all__ = [
    "DEFAULT_PII_PATTERNS",
    "PiiName",
    "PiiPattern",
    "luhn_valid",
]
