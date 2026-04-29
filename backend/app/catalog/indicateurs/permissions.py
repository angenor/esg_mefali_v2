"""F09 US1 — Permissions ``indicateur`` (admin only)."""

from __future__ import annotations

from app.auth.dependencies import get_current_admin

require_admin = get_current_admin
