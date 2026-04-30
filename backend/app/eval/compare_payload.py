"""F35 — Comparateur ``payload_partial`` ↔ ``actual`` (pure Python).

Supporte ``options_count_min``, ``options_count_max``, ``options_contain``,
``equals``, ``regex``. Renvoie ``(match, reason)``.
"""

from __future__ import annotations

import re
from typing import Any


def _option_labels(actual: dict[str, Any]) -> list[str]:
    """Extrait la liste des labels d'options de façon tolérante."""
    options = actual.get("options")
    if not isinstance(options, list):
        return []
    labels: list[str] = []
    for opt in options:
        if isinstance(opt, str):
            labels.append(opt)
        elif isinstance(opt, dict):
            label = opt.get("label") or opt.get("text") or opt.get("value")
            if label is not None:
                labels.append(str(label))
    return labels


def compare_payload(
    expected_partial: dict[str, Any],
    actual: dict[str, Any] | None,
) -> tuple[bool, str | None]:
    """Compare ``actual`` aux contraintes ``expected_partial``."""
    if not expected_partial:
        return True, None
    if actual is None:
        return False, "actual_payload_missing"

    if "options_count_min" in expected_partial:
        labels = _option_labels(actual)
        if len(labels) < int(expected_partial["options_count_min"]):
            return False, "options_count_min_violated"
    if "options_count_max" in expected_partial:
        labels = _option_labels(actual)
        if len(labels) > int(expected_partial["options_count_max"]):
            return False, "options_count_max_violated"

    if "options_contain" in expected_partial:
        wanted = expected_partial["options_contain"]
        if not isinstance(wanted, list):
            return False, "options_contain_not_a_list"
        labels = _option_labels(actual)
        for w in wanted:
            if not any(str(w).lower() in lbl.lower() for lbl in labels):
                return False, f"options_contain_missing:{w}"

    if "equals" in expected_partial:
        eq = expected_partial["equals"]
        if not isinstance(eq, dict):
            return False, "equals_not_a_dict"
        for k, v in eq.items():
            if actual.get(k) != v:
                return False, f"equals_mismatch:{k}"

    if "regex" in expected_partial:
        rx = expected_partial["regex"]
        if not isinstance(rx, dict):
            return False, "regex_not_a_dict"
        for k, pattern in rx.items():
            value = actual.get(k)
            if value is None:
                return False, f"regex_field_missing:{k}"
            try:
                if not re.search(str(pattern), str(value)):
                    return False, f"regex_mismatch:{k}"
            except re.error:
                return False, f"regex_invalid:{k}"

    return True, None
