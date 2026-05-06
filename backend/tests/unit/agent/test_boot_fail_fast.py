"""F55 / T023 — Boot fail-fast tests.

Vérifie que ``ensure_handlers_registered`` lève une ``HandlerRegistrationError``
quand un tool ``ToolCategory.MUTATION`` n'a pas de handler.
"""

from __future__ import annotations

import pytest
from pydantic import BaseModel, ConfigDict

from app.agent.mutation_handlers import (
    HandlerRegistrationError,
    ensure_handlers_registered,
    mutation_handler,
    reset_mutation_handlers,
)
from app.agent.state import ToolCategory
from app.orchestrator.tool_registry import (
    TOOL_REGISTRY,
    reset_registry,
    tool,
)

pytestmark = pytest.mark.unit


class _Args(BaseModel):
    model_config = ConfigDict(extra="forbid")
    x: str = "x"


@pytest.fixture(autouse=True)
def _isolate_registry():
    backup = dict(TOOL_REGISTRY)
    reset_registry()
    reset_mutation_handlers()
    yield
    reset_registry()
    reset_mutation_handlers()
    TOOL_REGISTRY.update(backup)


def test_clean_state_no_raise():
    # Pas de tools enregistrés → ensure ne raise pas.
    ensure_handlers_registered()


def test_mutation_tool_without_handler_raises():
    tool(
        name="update_test_thing",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_Args,
        category=ToolCategory.MUTATION,
    )
    with pytest.raises(HandlerRegistrationError, match="handler missing"):
        ensure_handlers_registered()


def test_mutation_tool_with_handler_no_raise():
    tool(
        name="update_test_thing",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_Args,
        category=ToolCategory.MUTATION,
    )

    @mutation_handler("update_test_thing")
    async def _h(args, ctx):
        from app.agent.state import MutationResult

        return MutationResult(
            entity_type="x", entity_id=ctx.account_id, fields_updated=[]
        )

    ensure_handlers_registered()


def test_ask_tool_does_not_need_handler():
    tool(
        name="ask_qcu_test",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_Args,
        category=ToolCategory.ASK,
    )
    ensure_handlers_registered()


def test_show_tool_does_not_need_handler():
    tool(
        name="show_kpi_test",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_Args,
        category=ToolCategory.SHOW,
    )
    ensure_handlers_registered()


def test_read_tool_does_not_need_handler():
    tool(
        name="recall_test",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_Args,
        category=ToolCategory.READ,
    )
    ensure_handlers_registered()


def test_double_handler_registration_raises():
    tool(
        name="update_xx",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_Args,
        category=ToolCategory.MUTATION,
    )

    @mutation_handler("update_xx")
    async def _h1(args, ctx):
        ...

    with pytest.raises(ValueError, match="déjà enregistré"):

        @mutation_handler("update_xx")
        async def _h2(args, ctx):
            ...


def test_non_async_handler_rejected():
    tool(
        name="update_yy",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_Args,
        category=ToolCategory.MUTATION,
    )
    with pytest.raises(TypeError, match="coroutine"):

        @mutation_handler("update_yy")
        def _sync_h(args, ctx):  # type: ignore[misc]
            return None


def test_requires_confirmation_propagates_to_tool_def():
    tool(
        name="delete_zz",
        description="d",
        use_when="u",
        dont_use_when="dnt",
        schema=_Args,
        category=ToolCategory.MUTATION,
    )

    @mutation_handler("delete_zz", requires_confirmation=True)
    async def _h(args, ctx):
        from app.agent.state import MutationResult

        return MutationResult(
            entity_type="x",
            entity_id=ctx.account_id,
            fields_updated=[],
        )

    assert TOOL_REGISTRY["delete_zz"].requires_confirmation is True
