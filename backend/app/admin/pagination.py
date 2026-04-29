"""F06 — Keyset cursor pagination helpers (opaque base64 JSON cursor).

Cursor encodes ``{created_at: ISO8601, id: UUID-str}``.
"""

from __future__ import annotations

import base64
import json
from datetime import datetime
from typing import Any

from fastapi import HTTPException, status


def encode_cursor(created_at: datetime, id_: Any) -> str:
    payload = json.dumps(
        {"created_at": created_at.isoformat(), "id": str(id_)},
        separators=(",", ":"),
    ).encode("utf-8")
    return base64.urlsafe_b64encode(payload).decode("ascii").rstrip("=")


def decode_cursor(cursor: str | None) -> dict[str, Any] | None:
    if not cursor:
        return None
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        data = json.loads(raw)
        if not isinstance(data, dict) or "created_at" not in data or "id" not in data:
            raise ValueError("cursor payload malformed")
        return {
            "created_at": datetime.fromisoformat(data["created_at"]),
            "id": data["id"],
        }
    except (ValueError, json.JSONDecodeError, base64.binascii.Error) as exc:  # type: ignore[attr-defined]
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "invalid_cursor", "message": "Curseur invalide."},
        ) from exc


def build_page(
    items: list[dict[str, Any]],
    limit: int,
    total_estimate: int,
) -> dict[str, Any]:
    """Slice ``items`` (already fetched ``limit+1``) into a page envelope."""
    has_more = len(items) > limit
    page_items = items[:limit]
    next_cursor = None
    if has_more and page_items:
        last = page_items[-1]
        next_cursor = encode_cursor(last["created_at"], last["id"])
    return {
        "items": page_items,
        "next_cursor": next_cursor,
        "total_estimate": int(total_estimate),
    }
