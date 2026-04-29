"""F06 — ETag helpers for optimistic concurrency.

Format simple : ``"v{int}"``. Échec If-Match → 412 Precondition Failed.
"""

from __future__ import annotations

from fastapi import HTTPException, status


def make_etag(version: int) -> str:
    """Return the ETag header value for a given version integer."""
    return f'"v{int(version)}"'


def parse_if_match(header: str | None) -> int:
    """Parse a client-provided If-Match header into the expected version.

    Raises 412 (HTTPException) if the header is missing or malformed.
    """
    if not header:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={"code": "if_match_required", "message": "Header If-Match requis."},
        )
    raw = header.strip().strip('"')
    if not raw.startswith("v"):
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={"code": "if_match_invalid", "message": "Format If-Match invalide."},
        )
    try:
        return int(raw[1:])
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={"code": "if_match_invalid", "message": "Format If-Match invalide."},
        ) from exc


def assert_version_match(expected: int, current: int) -> None:
    """Raise 412 if ``expected`` (from If-Match) ≠ ``current`` (DB row)."""
    if expected != current:
        raise HTTPException(
            status_code=status.HTTP_412_PRECONDITION_FAILED,
            detail={
                "code": "version_mismatch",
                "message": "La ressource a été modifiée entre-temps.",
                "expected": expected,
                "current": current,
            },
        )
