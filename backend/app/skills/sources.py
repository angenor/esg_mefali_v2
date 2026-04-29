"""F19 — Résolution des sources liées à une skill.

Charge titre, publisher, extrait court (≤200 caractères), URL, ID, en filtrant
sur ``verification_status='verified'``. Ne lit jamais les sources non vérifiées.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Any

from sqlalchemy.orm import Session

from app.models.source import Source

EXCERPT_MAX_CHARS = 200


@dataclass(frozen=True)
class ResolvedSource:
    """DTO immutable d'une source résolue prête à être citée par le LLM."""

    id: uuid.UUID
    title: str
    publisher: str
    url: str
    excerpt: str  # ≤ EXCERPT_MAX_CHARS chars

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "title": self.title,
            "publisher": self.publisher,
            "url": self.url,
            "excerpt": self.excerpt,
        }


def _truncate(text: str | None, limit: int = EXCERPT_MAX_CHARS) -> str:
    if not text:
        return ""
    s = text.strip()
    if len(s) <= limit:
        return s
    return s[: max(0, limit - 1)].rstrip() + "…"


def resolve_sources(
    source_ids: list[uuid.UUID] | list[str],
    session: Session,
) -> list[ResolvedSource]:
    """Charge les sources VERIFIED parmi ``source_ids``, dans l'ordre fourni.

    - Sources non-verified ou inexistantes → omises silencieusement (US7).
    - Excerpt = ``notes`` ou ``title`` tronqués à 200 caractères.
    """
    if not source_ids:
        return []

    norm_ids: list[uuid.UUID] = []
    for sid in source_ids:
        if isinstance(sid, uuid.UUID):
            norm_ids.append(sid)
            continue
        try:
            norm_ids.append(uuid.UUID(str(sid)))
        except (ValueError, AttributeError):
            continue

    if not norm_ids:
        return []

    rows = (
        session.query(Source)
        .filter(Source.id.in_(norm_ids))
        .filter(Source.verification_status == "verified")
        .all()
    )
    by_id = {row.id: row for row in rows}

    resolved: list[ResolvedSource] = []
    for sid in norm_ids:
        row = by_id.get(sid)
        if row is None:
            continue
        excerpt = _truncate(getattr(row, "notes", None) or row.title)
        resolved.append(
            ResolvedSource(
                id=row.id,
                title=row.title,
                publisher=row.publisher,
                url=row.url,
                excerpt=excerpt,
            )
        )
    return resolved


__all__ = ["EXCERPT_MAX_CHARS", "ResolvedSource", "resolve_sources"]
