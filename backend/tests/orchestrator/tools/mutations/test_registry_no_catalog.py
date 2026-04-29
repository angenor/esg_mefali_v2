"""F17 — Test garde-fou registry PME (US5, SC-005, FR-009).

Vérifie qu'aucun tool de mutation catalogue n'est exposé via
``register_mutation_tools()``.
"""

from __future__ import annotations

import pytest

from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.mutations import register_mutation_tools


@pytest.fixture(autouse=True)
def _registered() -> None:
    register_mutation_tools()


FORBIDDEN_NAMES = (
    "update_referentiel",
    "create_referentiel",
    "delete_referentiel",
    "update_fonds",
    "create_fonds",
    "delete_fonds",
    "update_offre",
    "create_offre",
    "delete_offre",
    "update_intermediaire",
    "create_intermediaire",
    "delete_intermediaire",
    "update_indicateur",
    "create_indicateur",
    "delete_indicateur",
    "update_source",
    "create_source",
    "delete_source",
    "update_skill",
    "create_skill",
    "delete_skill",
    "update_template",
    "create_template",
    "delete_template",
)


@pytest.mark.parametrize("forbidden", FORBIDDEN_NAMES)
def test_no_catalog_mutation_in_registry(forbidden: str) -> None:
    assert forbidden not in TOOL_REGISTRY, (
        f"Tool catalogue interdit dans le registry PME : {forbidden}"
    )


def test_p1_mutation_tools_registered() -> None:
    expected = {
        "update_company_profile",
        "create_project",
        "update_project",
        "delete_project",
    }
    assert expected.issubset(set(TOOL_REGISTRY.keys()))
