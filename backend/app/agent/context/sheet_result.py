"""F54 / FR-017 — Continuité conversationnelle après réponse bottom sheet.

Si le ``payload_json`` du dernier message utilisateur contient un
``sheet_result``, on injecte une note explicite dans le prompt pour que
l'agent ne re-pose **pas** la question et utilise directement la valeur
fournie.

Schéma minimal :
``{"tool": str, "value": str|number, "label": str, "payload"?: dict}``.

- ``tool`` : nom du tool d'origine (ex. ``ask_qcu``, ``ask_form``).
- ``value`` : valeur sélectionnée (str pour radio, number pour slider…).
- ``label`` : libellé affiché à l'utilisateur.
- ``payload`` (optionnel) : dict pour formulaires multi-champs (``ask_form``).

Tous les champs string passent par :func:`clean_user_str` (FR-013).
"""

from __future__ import annotations

import json
import logging
from typing import Any

from app.agent.context.escape import clean_user_str

logger = logging.getLogger(__name__)


def extract_sheet_result(last_user_message: dict[str, Any] | None) -> dict | None:
    """Extrait un ``sheet_result`` valide depuis ``last_user_message``.

    ``last_user_message`` est un dict du type ``{role, content, payload_json}``
    (provenant du chat F13). Si :

    - le dict est ``None`` ou
    - ``payload_json`` est absent / None / vide / non-dict ou
    - ``payload_json["sheet_result"]`` est absent ou
    - le sheet_result n'a pas la forme minimale ``{tool, value, label}``,

    retourne ``None`` (no-op silencieux côté builder).
    """
    if not last_user_message:
        return None

    payload = last_user_message.get("payload_json")
    if isinstance(payload, str):
        # Tolérance : payload_json sérialisé.
        try:
            payload = json.loads(payload)
        except (ValueError, TypeError):
            return None

    if not isinstance(payload, dict):
        return None

    sheet = payload.get("sheet_result")
    if not isinstance(sheet, dict):
        return None

    tool = sheet.get("tool")
    value = sheet.get("value")
    label = sheet.get("label")

    if not isinstance(tool, str) or not tool:
        return None
    if value is None:
        return None
    if not isinstance(label, str):
        return None

    out: dict[str, Any] = {
        "tool": tool,
        "value": value,
        "label": label,
    }
    payload_extra = sheet.get("payload")
    if isinstance(payload_extra, dict):
        out["payload"] = payload_extra
    return out


def render_sheet_result_note(sheet_result: dict | None) -> str | None:
    """Construit la note "ne re-pose pas la question" (FR-017).

    Tous les fields string sont escape (FR-013) avant insertion.
    Retourne ``None`` si ``sheet_result`` est ``None``.
    """
    if not sheet_result:
        return None

    tool = clean_user_str(str(sheet_result.get("tool") or ""))
    label = clean_user_str(str(sheet_result.get("label") or ""))
    value_raw = sheet_result.get("value")
    if isinstance(value_raw, (int, float)):
        value_str = clean_user_str(str(value_raw))
    else:
        value_str = clean_user_str(str(value_raw) if value_raw is not None else "")

    payload = sheet_result.get("payload")
    payload_lines: list[str] = []
    if isinstance(payload, dict):
        for k, v in payload.items():
            k_clean = clean_user_str(str(k))
            v_clean = clean_user_str(str(v) if v is not None else "")
            payload_lines.append(f"  - {k_clean} : {v_clean}")

    body = [
        "# RÉPONSE BOTTOM SHEET (au tour précédent)",
        f"L'utilisateur a répondu via une bottom sheet associée au tool `{tool}` :",
        f"- Question / libellé : {label}",
        f"- Valeur sélectionnée : `{value_str}`",
    ]
    if payload_lines:
        body.append("- Champs détaillés :")
        body.extend(payload_lines)
    body.append(
        "\nNe re-pose pas cette question. Utilise la valeur ci-dessus comme "
        "réponse acquise et continue le flux."
    )
    return "\n".join(body)


__all__ = ["extract_sheet_result", "render_sheet_result_note"]
