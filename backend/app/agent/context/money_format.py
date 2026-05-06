"""F54 / NFR-006 — Affichage monétaire multi-devise pour le system prompt.

Conventions (P5) :

- Toute valeur monétaire est exposée comme :class:`Money` (Decimal + ISO 4217).
- Affichage par défaut : devise native uniquement (ex. ``"15 000 000 XOF"``).
- Si la PME mélange plusieurs devises (ex. projets en XOF + candidatures en
  EUR), on annote d'un équivalent XOF entre parenthèses
  (``"100 EUR (~65 596 XOF)"``).
- XOF ↔ EUR utilise le peg fixe officiel UEMOA : 1 EUR = 655.957 XOF.
- USD ↔ XOF via un snapshot quotidien ``fx_rate`` (fourni en paramètre par
  l'appelant ; ``None`` → pas d'équivalent).
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

#: Peg fixe FCFA-EUR officiel UEMOA — sourcé (P5).
FX_PEG_XOF_EUR: Decimal = Decimal("655.957")


@dataclass(frozen=True)
class Money:
    """Valeur monétaire typée (P5) — n'utilise jamais ``float``.

    Représentation interne : :class:`Decimal` + code ISO 4217 trois lettres.
    """

    amount: Decimal
    currency: str

    def __post_init__(self) -> None:
        if not isinstance(self.amount, Decimal):
            object.__setattr__(self, "amount", Decimal(str(self.amount)))
        if not isinstance(self.currency, str) or len(self.currency) != 3:
            raise ValueError("Money.currency must be a 3-letter ISO 4217 code")
        # Normaliser en majuscules (immutability-safe via object.__setattr__).
        object.__setattr__(self, "currency", self.currency.upper())


def collect_currencies(values: Iterable[Money | None]) -> set[str]:
    """Collecte les devises distinctes d'un itérable de :class:`Money` (None
    ignoré). Utile pour décider d'afficher ou non un équivalent XOF dans le
    prompt (NFR-006).
    """
    out: set[str] = set()
    for m in values:
        if m is not None and m.currency:
            out.add(m.currency)
    return out


def format_money(
    m: Money,
    *,
    native_currencies: set[str],
    fx_rate_usd_to_xof: Decimal | None = None,
) -> str:
    """Formate ``m`` pour insertion dans le system prompt.

    Règles :
    - Si ``len(native_currencies) <= 1`` ou ``m.currency == "XOF"``,
      retour : ``"15 000 000 XOF"`` (devise native uniquement).
    - Sinon, ajoute ``" (~65 596 XOF)"`` quand la conversion est possible.
      EUR utilise le peg fixe ; USD utilise ``fx_rate_usd_to_xof`` si fourni.
      Pour toute autre devise (MAD, CDF, ...), on n'affiche pas d'équivalent
      (soft-fail).
    """
    base = f"{_format_amount(m.amount)} {m.currency}"

    multi = len(native_currencies) > 1
    if not multi:
        return base

    # Pas d'équivalent si on est déjà en XOF (tautologie).
    if m.currency == "XOF":
        return base

    equivalent_xof = _convert_to_xof(m, fx_rate_usd_to_xof=fx_rate_usd_to_xof)
    if equivalent_xof is None:
        return base

    return f"{base} (~{_format_amount(equivalent_xof)} XOF)"


def _convert_to_xof(
    m: Money, *, fx_rate_usd_to_xof: Decimal | None
) -> Decimal | None:
    """Convertit un montant en XOF si possible, sinon ``None``."""
    if m.currency == "XOF":
        return m.amount
    if m.currency == "EUR":
        return (m.amount * FX_PEG_XOF_EUR).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    if m.currency == "USD" and fx_rate_usd_to_xof is not None:
        return (m.amount * fx_rate_usd_to_xof).quantize(
            Decimal("1"), rounding=ROUND_HALF_UP
        )
    return None


def _format_amount(amount: Decimal) -> str:
    """Formate un :class:`Decimal` avec espace fine comme séparateur de
    milliers : ``Decimal("15000000")`` → ``"15 000 000"``.

    Conserve les décimales si présentes (ex. ``"1 234.56"``).
    """
    # Quantize les valeurs entières pour éviter ``"1.0"``.
    if amount == amount.to_integral_value():
        s = str(int(amount))
    else:
        s = format(amount.normalize(), "f")
    # Insère un espace tous les 3 chars en partant de la droite (sur la part
    # entière).
    if "." in s:
        int_part, _, dec_part = s.partition(".")
        return _group_thousands(int_part) + "." + dec_part
    return _group_thousands(s)


def _group_thousands(s: str) -> str:
    if not s:
        return s
    sign = ""
    if s.startswith("-"):
        sign, s = "-", s[1:]
    parts: list[str] = []
    i = len(s)
    while i > 3:
        parts.append(s[i - 3:i])
        i -= 3
    parts.append(s[:i])
    return sign + " ".join(reversed(parts))


__all__ = [
    "FX_PEG_XOF_EUR",
    "Money",
    "collect_currencies",
    "format_money",
]
