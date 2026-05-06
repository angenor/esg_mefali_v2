"""F56 / FR-001 — Détecteur de claims factuels (synchrone, regex+keywords).

Algorithme :
1. Découper ``text`` en phrases via ponctuation (``.``, ``?``, ``!``).
2. Pour chaque phrase whitelistée, ne rien extraire.
3. Sinon, appliquer les regex de chaque ``ClaimKind`` (sur la phrase, en
   préservant les offsets globaux).
4. Trier par ``span[0]`` croissant ; dédup ``(span, kind)``.
5. Marquer ``from_tool=True`` si la sous-chaîne ``raw`` apparaît dans
   l'un des ``tool_outputs`` (substring ``in``, case-insensitive).

Performance cible : < 50 ms p95 pour 2 000 caractères (NFR-001). On
compile une fois les regex au chargement et on parcourt le texte une
seule fois par kind.

Synchrone, aucune dépendance LLM (NFR-005).
"""

from __future__ import annotations

import re
from collections.abc import Iterable

from app.agent.sourcing.models import Claim, ClaimKind
from app.agent.sourcing.whitelist import is_whitelisted

# ---------------------------------------------------------------------------
# Pré-compilation des regex par ``ClaimKind``
# ---------------------------------------------------------------------------

# Unités numériques : un nombre (entier ou décimal, sep , ou .) suivi d'une
# unité courante ESG/finance.
# Examples :
# - "6.0 kg CO2/litre"
# - "1200 kWh"
# - "50 M USD"
# - "10 000 EUR"
_UNIT_BODIES = (
    r"kg(?:[\s/-]?(?:co2|co₂|équivalent|eq))?(?:[\s/-]?(?:l|litre|kg|kw|km))?",
    r"co2|co₂",
    r"kwh|mwh|gwh|kw|mw|gw",
    r"litres?|l\b",
    r"tonnes?|t\b",
    r"m³|m3",
    r"%\s*",  # rare unit-only context — handled in percentage
    r"usd|eur|xof|xaf|gbp|cny|cfa|fcfa|us\$",
    r"hectares?|ha\b",
    r"jours?|j\b|semaines?|mois|ans?",
)
_UNIT_ALT = "|".join(_UNIT_BODIES)
# Optional magnitude prefix (M, Md, Mds, milliard(s), million(s))
_MAG = r"(?:M|Md|Mds?|millions?|milliards?|k|K)"
# Number with optional thousand sep (' ' or '.' or ',') + optional decimal
_NUMBER = r"\d{1,3}(?:[.\s]\d{3})*(?:[.,]\d+)?|\d+(?:[.,]\d+)?"

NUMBER_WITH_UNIT_RE = re.compile(
    rf"\b(?:{_NUMBER})\s*(?:{_MAG}\s+)?(?:{_UNIT_ALT})\b",
    re.IGNORECASE,
)

# Percentage : "15%", "4,5 %", "20 pour cent"
PERCENTAGE_RE = re.compile(
    rf"\b(?:{_NUMBER})\s*%"
    rf"|\b(?:{_NUMBER})\s+pour\s+cent\b",
    re.IGNORECASE,
)

# Range : "entre X et Y", "X-Y unit", "de X à Y"
RANGE_RE = re.compile(
    r"\bentre\s+(?:" + _NUMBER + r")\s+et\s+(?:" + _NUMBER + r")\b"
    r"|\bde\s+(?:" + _NUMBER + r")\s+à\s+(?:" + _NUMBER + r")\b"
    r"|\b(?:" + _NUMBER + r")\s*[-–]\s*(?:" + _NUMBER + r")\s*"
    r"(?:" + _UNIT_ALT + r"|semaines?|mois|ans?)\b",
    re.IGNORECASE,
)

# Ratio : "3:1", "1 pour 4", "2/3"
RATIO_RE = re.compile(
    r"\b\d+\s*[:/]\s*\d+\b"
    r"|\b(?:un|une|\d+)\s+pour\s+\d+\b"
    r"|\bratio\s+de\s+\d+\s+pour\s+\d+\b",
    re.IGNORECASE,
)

# Reference keywords : organismes ESG/finance reconnus
_REFERENCE_KEYWORDS = (
    "ADEME",
    "GCF",
    "BOAD",
    "BCEAO",
    "BEI",
    "AFD",
    "Banque Mondiale",
    "World Bank",
    "FMI",
    "OCDE",
    "GIEC",
    "IPCC",
    "GHG Protocol",
    "TCFD",
    "GRI",
    "SASB",
    "ISO 14001",
    "ISO 14064",
    "BAD",
    "UEMOA",
    "IFC",
)
REFERENCE_KEYWORD_RE = re.compile(
    r"\b(?:" + "|".join(re.escape(k) for k in _REFERENCE_KEYWORDS) + r")\b"
)

# Threshold : "seuil de X", "minimum de X", "plafond de X", "limite de X"
# On capture une fenêtre raisonnable autour du mot-clé pour englober la valeur
THRESHOLD_RE = re.compile(
    r"\b(?:seuil|minimum|maximum|plafond|limite|borne)\b"
    r"(?:[\w\s,\.'éàèùûôâ]*?\d[\d\s.,]*\s*(?:" + _UNIT_ALT + r"|"
    + _MAG + r"\s*(?:" + _UNIT_ALT + r"|))?)",
    re.IGNORECASE,
)

# Formula : "x = y", "calcul: x = y", "formule: x = y"
FORMULA_RE = re.compile(
    r"\b[a-zA-Zà-ÿÀ-Ÿ_][\w\s]*\s*=\s*[\w\s\*\+\-/]+",
    re.IGNORECASE,
)


_KIND_RE: tuple[tuple[ClaimKind, re.Pattern[str]], ...] = (
    ("formula", FORMULA_RE),
    ("threshold", THRESHOLD_RE),
    ("range", RANGE_RE),
    ("percentage", PERCENTAGE_RE),
    ("ratio", RATIO_RE),
    ("number_with_unit", NUMBER_WITH_UNIT_RE),
    ("reference_keyword", REFERENCE_KEYWORD_RE),
)


_SENTENCE_END_RE = re.compile(r"(?<=[\.\?\!])\s+|\n\n+")


def _split_sentences_with_offsets(text: str) -> list[tuple[int, int]]:
    """Découpe ``text`` en (start, end) phrases (offsets globaux).

    Conserve toujours au moins une phrase couvrant tout le texte.
    """
    if not text:
        return []
    boundaries: list[int] = [0]
    for m in _SENTENCE_END_RE.finditer(text):
        boundaries.append(m.end())
    boundaries.append(len(text))
    spans: list[tuple[int, int]] = []
    for i in range(len(boundaries) - 1):
        s, e = boundaries[i], boundaries[i + 1]
        if e > s:
            spans.append((s, e))
    return spans


def _matches_in(
    pat: re.Pattern[str], text: str, *, base_offset: int = 0
) -> Iterable[tuple[int, int, str]]:
    for m in pat.finditer(text):
        yield (base_offset + m.start(), base_offset + m.end(), m.group(0))


def _find_overlapping_claims_in_sentence(
    sentence: str, *, base_offset: int
) -> list[Claim]:
    """Extrait les claims dans ``sentence``. Dédup par ``(span, kind)``.

    Note : ne déduplique PAS entre kinds (un nombre + son unité peut être
    aussi un threshold). Cela permet de mettre plusieurs facettes sur un
    même chiffre. La dédup finale globale (même span ET même kind) se
    fait dans ``detect_claims``.
    """
    found: list[Claim] = []
    for kind, pat in _KIND_RE:
        for s, e, raw in _matches_in(pat, sentence, base_offset=base_offset):
            found.append(Claim(span=(s, e), kind=kind, raw=raw, from_tool=False))
    return found


def _is_from_tool(raw: str, tool_outputs: list[str]) -> bool:
    if not tool_outputs:
        return False
    needle = raw.lower().strip()
    if not needle:
        return False
    for out in tool_outputs:
        if out and needle in out.lower():
            return True
    return False


def detect_claims(
    text: str,
    *,
    tool_outputs: list[str] | None = None,
) -> list[Claim]:
    """Detect factual claims in ``text``.

    Args:
        text: Assistant response text. FR uniquement en MVP.
        tool_outputs: Liste de chaînes (concat des ToolMessage du tour).
            Utilisé pour marquer ``from_tool=True``.

    Returns:
        Liste de ``Claim`` triée par ``span[0]`` croissant. Aucune duplication
        ``(span, kind)``.
    """
    if not text:
        return []
    if tool_outputs is None:
        tool_outputs = []

    sentence_spans = _split_sentences_with_offsets(text)
    all_claims: list[Claim] = []

    for s, e in sentence_spans:
        sentence = text[s:e]
        if is_whitelisted(sentence):
            continue
        all_claims.extend(
            _find_overlapping_claims_in_sentence(sentence, base_offset=s)
        )

    # Marquage from_tool
    if tool_outputs:
        all_claims = [
            Claim(
                span=c.span,
                kind=c.kind,
                raw=c.raw,
                from_tool=_is_from_tool(c.raw, tool_outputs),
            )
            for c in all_claims
        ]

    # Tri stable + dédup (span, kind)
    all_claims.sort(key=lambda c: (c.span[0], c.span[1], c.kind))
    seen: set[tuple[tuple[int, int], str]] = set()
    deduped: list[Claim] = []
    for c in all_claims:
        key = (c.span, c.kind)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(c)
    return deduped


__all__ = ["detect_claims"]
