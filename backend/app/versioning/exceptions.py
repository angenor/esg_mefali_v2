"""F04 — Versioning exceptions."""

from __future__ import annotations


class OptimisticLockError(Exception):
    """Raised when ``publish_new_version`` is called with a stale version_at_load.

    Mapped to HTTP 412 Precondition Failed by the FastAPI router.
    """

    def __init__(self, current_version: int, expected: int) -> None:
        super().__init__(
            f"Optimistic lock violation: expected version={expected}, "
            f"current version={current_version}"
        )
        self.current_version = current_version
        self.expected = expected
