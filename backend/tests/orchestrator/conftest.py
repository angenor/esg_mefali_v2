"""Conftest minimal pour les tests F14 orchestrator (sans DB ni LLM réel)."""

from __future__ import annotations

import pytest

from app.orchestrator import tool_registry


@pytest.fixture(autouse=True)
def _reset_tool_registry() -> None:
    """Garantit l'isolation : chaque test démarre avec un registre vide."""
    tool_registry.reset_registry()
    yield
    tool_registry.reset_registry()
