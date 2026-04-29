"""Conftest pour les tests F15 — registre tools propre par test."""

from __future__ import annotations

import pytest

from app.orchestrator import tool_registry


@pytest.fixture(autouse=True)
def _reset_tool_registry() -> None:
    """Garantit l'isolation : chaque test démarre avec un registre vide."""
    tool_registry.reset_registry()
    yield
    tool_registry.reset_registry()
