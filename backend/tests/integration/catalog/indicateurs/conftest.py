"""F09 — réexpose les fixtures admin de F06/F08."""

from __future__ import annotations

from tests.integration.admin.conftest import (  # noqa: F401
    admin_client,
    pending_source,
    pme_client,
    verified_source,
)
