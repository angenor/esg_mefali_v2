"""F55 — Helper ``format_event`` pour les frames SSE.

Format générique conforme à la spec EventSource :
``event: <type>\\ndata: <json>\\n[id: <id>\\n]\\n``.

Quand ``dry_run=True``, le ``event_type`` est préfixé ``dry_run:``
(cf. ``contracts/sse-events.md``).

Ce module est sans état et utilisé par ``sse_bridge`` + ``runner``.
"""

from __future__ import annotations

import json
from typing import Any


def format_event(
    event_type: str,
    data: dict[str, Any],
    *,
    event_id: str | None = None,
    dry_run: bool = False,
) -> str:
    """Sérialise un event SSE.

    Paramètres :
    - ``event_type`` : nom de l'event (text_delta, tool_invoke, mutation, ...).
    - ``data`` : payload JSON sérialisable.
    - ``event_id`` : id optionnel pour reconnexion ``Last-Event-ID``.
    - ``dry_run`` : préfixe ``dry_run:`` au type (US6).
    """
    if not event_type:
        raise ValueError("event_type required")

    prefix = "dry_run:" if dry_run else ""
    full_type = f"{prefix}{event_type}"

    parts = [f"event: {full_type}\n"]
    if event_id:
        parts.append(f"id: {event_id}\n")
    payload = json.dumps(data, ensure_ascii=False, default=str)
    parts.append(f"data: {payload}\n\n")
    return "".join(parts)


__all__ = ["format_event"]
