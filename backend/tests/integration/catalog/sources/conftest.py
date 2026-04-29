"""F07 — fixtures locales : réutilise admin_client/pme_client de F06."""

from __future__ import annotations

# Réexporter les fixtures admin_client et pme_client définies dans
# tests/integration/admin/conftest.py pour qu'elles soient disponibles
# pour les tests sous tests/integration/catalog/sources/.
from tests.integration.admin.conftest import (  # noqa: F401
    admin_client,
    pme_client,
)
