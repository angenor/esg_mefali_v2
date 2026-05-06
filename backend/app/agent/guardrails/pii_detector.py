"""F58 — PII detector + masker (FR-003, FR-004).

``mask_pii(text)`` retourne une COPIE masquée du texte + le nombre de PII
masquées. Ne mute jamais le texte original.

Le message conversation envoyé au LLM reste intact (besoin métier) ; seule
la version persistée en base (``agent_run``, ``agent_run_step``,
``tool_call_log``) est masquée.

Latence cible : < 10 ms p99 sur texte 1 KB.
"""

from __future__ import annotations

from collections.abc import Iterable

from app.agent.guardrails.pii_patterns import (
    DEFAULT_PII_PATTERNS,
    PiiPattern,
    luhn_valid,
)


def mask_pii(
    text: str,
    patterns: Iterable[PiiPattern] = DEFAULT_PII_PATTERNS,
) -> tuple[str, int]:
    """Retourne (masked_text, count) — immutable, ne mute jamais ``text``.

    Pour ``card_luhn``, on vérifie la validité Luhn AVANT masquage afin
    d'éviter les faux positifs sur des séquences aléatoires de chiffres.

    Returns:
        (masked_text, count) où ``count`` = nombre d'occurrences masquées.
    """
    if not text:
        return text, 0

    out = text
    count = 0
    masked_spans: list[tuple[int, int]] = []  # pour éviter les overlaps

    for pattern in patterns:
        # Itère sur les matches en évitant ceux déjà masqués
        for m in list(pattern.regex.finditer(out)):
            start, end = m.start(), m.end()
            # Skip si overlap avec un précédent masquage
            if any(s <= start < e or s < end <= e for s, e in masked_spans):
                continue
            matched = m.group(0)
            if pattern.requires_luhn_check:
                digits_only = "".join(ch for ch in matched if ch.isdigit())
                if not luhn_valid(digits_only):
                    continue
            # Substitution non destructive : on rebuild la string
            out = out[:start] + pattern.mask_template + out[end:]
            count += 1
            # Adjust span tracking après changement de longueur
            new_end = start + len(pattern.mask_template)
            masked_spans.append((start, new_end))
            # Décale les spans suivants
            offset = new_end - end
            masked_spans = [
                (s + offset, e + offset) if s > start else (s, e)
                for s, e in masked_spans
            ]
            # Comme la string a changé de longueur, on a besoin de re-itérer
            # Mais on a déjà absorbé ce match donc continue le for
        # Re-search dans la nouvelle out pour le pattern suivant ; les spans
        # sont régulièrement re-calculés par re.finditer.
    return out, count


__all__ = ["mask_pii"]
