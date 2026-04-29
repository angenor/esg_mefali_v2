"""F10 T014 — unit tests for ``app.admin.deps``."""

from __future__ import annotations

from app.admin.deps import ADMIN_MUTATION_WHITELIST, require_admin
from app.auth.dependencies import get_current_admin


def test_require_admin_alias_points_to_get_current_admin() -> None:
    assert require_admin is get_current_admin


def test_admin_mutation_whitelist_is_tuple_of_pairs() -> None:
    assert isinstance(ADMIN_MUTATION_WHITELIST, tuple)
    for entry in ADMIN_MUTATION_WHITELIST:
        assert isinstance(entry, tuple)
        assert len(entry) == 2
        method, path = entry
        assert method in {"POST", "PUT", "PATCH", "DELETE"}
        assert path.startswith("/admin/")


def test_admin_mutation_whitelist_contains_known_endpoints() -> None:
    paths = {p for _, p in ADMIN_MUTATION_WHITELIST}
    assert "/admin/users/{user_id}/reset-password" in paths
    assert "/admin/attestations/{att_id}/revoke" in paths
