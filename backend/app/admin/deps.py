"""F10 — Admin dependencies.

Re-exports F02 ``get_current_admin`` as ``require_admin`` and provides
``AdminWhitelistGuard`` (T052 — placeholder MVP).
"""

from __future__ import annotations

from app.auth.dependencies import get_current_admin

# Public alias (US1..US4 expectation).
require_admin = get_current_admin


# T052 — Whitelist of allowed mutations on /admin/* (MVP scope).
# Each entry is (method, path_pattern). For MVP we expose the list for
# documentation/testing purposes; full middleware enforcement is DEFERRED.
ADMIN_MUTATION_WHITELIST: tuple[tuple[str, str], ...] = (
    ("POST", "/admin/users/{user_id}/reset-password"),
    ("POST", "/admin/users/{user_id}/unlock"),
    ("POST", "/admin/attestations/{att_id}/revoke"),
    ("POST", "/admin/attestations/{att_id}/regenerate"),
    ("POST", "/admin/llm-pricing"),
)
