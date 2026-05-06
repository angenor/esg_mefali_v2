"""F56 / T010 — Test unit de l'enregistrement des 3 sourcing tools."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.agent.sourcing.tool_schemas import (
    CiteSourceArgs,
    FlagUnsourcedArgs,
    SearchSourceArgs,
)
from app.agent.state import ToolCategory
from app.orchestrator.tool_registry import TOOL_REGISTRY


@pytest.fixture(autouse=True)
def _ensure_registry_loaded() -> None:
    # Force le chargement des registrations F56 (idempotent).
    import app.orchestrator.tools.sourcing  # noqa: F401


@pytest.mark.unit
def test_cite_source_registered_as_read() -> None:
    assert "cite_source" in TOOL_REGISTRY
    tdef = TOOL_REGISTRY["cite_source"]
    assert tdef.category == ToolCategory.READ
    assert tdef.schema is CiteSourceArgs


@pytest.mark.unit
def test_search_source_registered_as_read() -> None:
    assert "search_source" in TOOL_REGISTRY
    tdef = TOOL_REGISTRY["search_source"]
    assert tdef.category == ToolCategory.READ
    assert tdef.schema is SearchSourceArgs


@pytest.mark.unit
def test_flag_unsourced_registered_as_mutation() -> None:
    assert "flag_unsourced" in TOOL_REGISTRY
    tdef = TOOL_REGISTRY["flag_unsourced"]
    assert tdef.category == ToolCategory.MUTATION
    assert tdef.schema is FlagUnsourcedArgs


@pytest.mark.unit
def test_cite_source_schema_rejects_extra_fields() -> None:
    from uuid import uuid4

    with pytest.raises(ValidationError):
        CiteSourceArgs(source_id=uuid4(), extra_field="x")  # type: ignore[call-arg]


@pytest.mark.unit
def test_search_source_schema_validation() -> None:
    SearchSourceArgs(query="hello", limit=5)
    with pytest.raises(ValidationError):
        SearchSourceArgs(query="", limit=5)
    with pytest.raises(ValidationError):
        SearchSourceArgs(query="x" * 600, limit=5)


@pytest.mark.unit
def test_flag_unsourced_schema_validation() -> None:
    FlagUnsourcedArgs(claim="claim", reason="reason")
    with pytest.raises(ValidationError):
        FlagUnsourcedArgs(claim="", reason="reason")
    with pytest.raises(ValidationError):
        FlagUnsourcedArgs(claim="x" * 1100, reason="reason")
