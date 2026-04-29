"""F04 — Field-blacklist redaction for audit-log payloads (FR-013, SC-010).

The redaction is applied recursively to dict / list / tuple structures so that
nested forms (e.g. ``{"profile": {"password": "x"}}``) are scrubbed too.
"""

from __future__ import annotations

from typing import Any

REDACTED = "[REDACTED]"

#: Field names whose values must NEVER appear in audit_log rows.
AUDIT_REDACTION_FIELDS: tuple[str, ...] = (
    "password",
    "password_hash",
    "jwt",
    "access_token",
    "refresh_token",
    "secret",
    "api_key",
    "client_secret",
    "private_key",
    "csrf_token",
)

_REDACTED_SET = frozenset(AUDIT_REDACTION_FIELDS)


def _matches(field_name: str) -> bool:
    """Case-insensitive blacklist match (also matches ``user_password``, etc.)."""
    name = field_name.lower()
    return any(token in name for token in _REDACTED_SET)


def redact(value: Any, *, key: str | None = None) -> Any:
    """Return a deeply-redacted copy of ``value``.

    - If ``key`` matches the blacklist, the entire value is replaced by
      :data:`REDACTED`, regardless of its shape.
    - For dicts: recurse on each ``(k, v)`` pair, redacting blacklisted keys.
    - For lists/tuples: recurse element-wise.
    - For scalars: return unchanged (immutable).
    """
    if key is not None and _matches(key):
        return REDACTED
    if isinstance(value, dict):
        return {k: redact(v, key=k) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if isinstance(value, tuple):
        return tuple(redact(v) for v in value)
    return value


def redact_field(field: str | None, value: Any) -> Any:
    """Top-level redaction entrypoint used by :func:`record_audit`.

    If ``field`` itself is blacklisted -> replace the value entirely.
    Otherwise, recurse into structured values.
    """
    if field is not None and _matches(field):
        return REDACTED
    return redact(value)
