"""F20 — Anti-injection scanner pour ``prompt_expert`` des skills.

Détecte les patterns d'injection courants, les caractères de contrôle
anormaux, et les fuites éventuelles de secrets en dur. Utilisé au save
et au publish d'une skill (US7).

API publique : ``scan(text) -> list[Issue]``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Final


@dataclass(frozen=True)
class Issue:
    """Une détection anti-injection."""

    code: str
    message: str
    excerpt: str


_INJECTION_PATTERNS: Final[tuple[tuple[str, str, str, int], ...]] = (
    (
        r"ignore\s+(?:all\s+|the\s+|any\s+)?previous\s+instructions",
        "ignore_previous",
        "Tentative de neutralisation des instructions précédentes.",
        re.IGNORECASE,
    ),
    (
        r"\byou\s+are\s+now\b",
        "role_takeover_en",
        "Tentative de réassignation de rôle (anglais).",
        re.IGNORECASE,
    ),
    (
        r"\btu\s+es\s+(?:désormais|maintenant)\b",
        "role_takeover_fr",
        "Tentative de réassignation de rôle (français).",
        re.IGNORECASE,
    ),
    (
        r"</system>|<system>",
        "system_tag",
        "Balise système trouvée — risque d'injection structurée.",
        0,
    ),
    (
        r"(?m)^\s*system\s*:",
        "system_prefix",
        "Préfixe 'system:' en début de ligne — risque d'injection.",
        0,
    ),
    (
        r"sk-[A-Za-z0-9]{20,}",
        "openai_key_leak",
        "Possible fuite de clé OpenAI.",
        0,
    ),
    (
        r"ghp_[A-Za-z0-9]{20,}",
        "github_token_leak",
        "Possible fuite de token GitHub.",
        0,
    ),
)


# Caractères de contrôle interdits (sauf \n=0x0A, \t=0x09, \r=0x0D).
_CONTROL_CHAR_RE: Final[re.Pattern[str]] = re.compile(r"[\x00-\x08\x0B\x0C\x0E-\x1F]")


def _excerpt(text: str, match: re.Match[str], width: int = 80) -> str:
    start = max(match.start() - 20, 0)
    end = min(match.end() + 20, len(text))
    raw = text[start:end].replace("\n", " ").replace("\r", " ").strip()
    return raw[:width]


def scan(text: str) -> list[Issue]:
    """Scanne ``text`` et retourne la liste des issues détectées."""
    if not text:
        return []
    issues: list[Issue] = []
    for pattern, code, message, flags in _INJECTION_PATTERNS:
        for match in re.finditer(pattern, text, flags=flags):
            issues.append(Issue(code=code, message=message, excerpt=_excerpt(text, match)))
    for match in _CONTROL_CHAR_RE.finditer(text):
        issues.append(
            Issue(
                code="control_char",
                message=f"Caractère de contrôle interdit (0x{ord(match.group(0)):02X}).",
                excerpt=_excerpt(text, match),
            )
        )
    return issues


def issues_to_dict(issues: list[Issue]) -> list[dict[str, str]]:
    """Sérialise les issues pour la réponse HTTP."""
    return [{"code": i.code, "message": i.message, "excerpt": i.excerpt} for i in issues]


__all__ = ["Issue", "scan", "issues_to_dict"]
