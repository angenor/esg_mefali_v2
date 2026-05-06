"""F57 / US7 — Tests unit ``entity_memory.update_entity_memory`` + hook.

Tests UNIT (mock DB + LLM). L'audit + UPSERT réels sont testés en
intégration (test_memory_rls_entity_memory + test_memory_recall_log).
"""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.agent.memory.entity_memory import (
    DELETE_TOOLS,
    ENTITY_TABLE_MAP,
    TOOL_ENTITY_TYPE_MAP,
    build_after_dispatch_hook,
    build_before_dispatch_hook,
    update_entity_memory,
)

pytestmark = pytest.mark.unit


def test_entity_table_map_keys() -> None:
    """Les 4 entity_types canoniques sont mappés."""
    assert set(ENTITY_TABLE_MAP.keys()) == {
        "Entreprise",
        "Projet",
        "Candidature",
        "Indicateur",
    }


def test_tool_entity_type_map_includes_known_tools() -> None:
    assert TOOL_ENTITY_TYPE_MAP["update_company_profile"] == "Entreprise"
    assert TOOL_ENTITY_TYPE_MAP["delete_project"] == "Projet"


def test_delete_tools_includes_delete_project() -> None:
    assert "delete_project" in DELETE_TOOLS


def test_update_entity_memory_unsupported_type_no_op() -> None:
    """Type inconnu → no-op silencieux, pas de DB call."""
    asyncio.run(
        update_entity_memory(
            account_id=uuid4(),
            entity_type="Bogus",  # type: ignore[arg-type]
            entity_id=uuid4(),
        )
    )


def test_update_entity_memory_purge_calls_delete() -> None:
    """purge=True → DELETE entity_memory + audit ; pas de LLM call."""
    aid = uuid4()
    eid = uuid4()
    deleted = []

    class _Sess:
        def execute(self, *a: Any, **kw: Any) -> Any:
            return None

        def commit(self) -> None:
            pass

        def rollback(self) -> None:
            pass

        def close(self) -> None:
            pass

    def _delete(db, *, account_id, entity_type, entity_id):  # noqa: ANN001
        deleted.append((account_id, entity_type, entity_id))
        return 1

    def _audit(db, **kw):  # noqa: ANN001
        return uuid4()

    import app.db as _db

    with patch.object(_db, "SessionLocal", return_value=_Sess()), patch(
        "app.agent.memory.entity_memory.delete_entity_memory", side_effect=_delete
    ), patch(
        "app.agent.memory.entity_memory.write_audit_entity_memory", side_effect=_audit
    ), patch(
        "app.agent.memory.entity_memory._llm_summarize_entity"
    ) as mock_llm:
        asyncio.run(
            update_entity_memory(
                account_id=aid,
                entity_type="Projet",
                entity_id=eid,
                purge=True,
            )
        )
    assert deleted == [(aid, "Projet", eid)]
    mock_llm.assert_not_called()


def test_after_hook_skips_when_status_not_ok() -> None:
    """Hook : si status != 'ok' → no-op."""
    hook = build_after_dispatch_hook()

    class _Call:
        name = "update_company_profile"

    class _Result:
        status = "error"
        entity_type = "Entreprise"
        entity_id = uuid4()

    asyncio.run(hook(_Call(), _Result()))
    # Pas d'erreur attendue ; pas de side-effect mesurable ici (on regarde
    # juste que ça ne crash pas).


def test_after_hook_runs_for_ok_with_entity() -> None:
    """Hook : ok + entity_type + entity_id → schedule task (best-effort)."""
    before_hook = build_before_dispatch_hook()
    after_hook = build_after_dispatch_hook()

    class _State:
        account_id = uuid4()
        user_id = uuid4()
        agent_run_id = None

    state = _State()

    class _Call:
        name = "update_company_profile"

    class _Result:
        status = "ok"
        entity_type = "Entreprise"
        entity_id = uuid4()

    # Pas de loop async actif → asyncio.create_task() lèverait, mais le
    # hook absorbe via try/except.

    async def _run() -> None:
        await before_hook(_Call(), state)
        # Le after_hook va appeler asyncio.create_task ; il faut donc être
        # dans un event loop, ce qui est le cas via asyncio.run ci-dessous.
        with patch(
            "app.agent.memory.entity_memory.update_entity_memory"
        ) as mock_upd:
            # mock_upd doit retourner une coroutine pour create_task
            async def _noop(**kw: Any) -> None:
                return None

            mock_upd.side_effect = _noop
            await after_hook(_Call(), _Result())
            await asyncio.sleep(0)  # yield to scheduled task
            assert mock_upd.called

    asyncio.run(_run())


def test_after_hook_resolves_entity_type_from_tool_name() -> None:
    """Si result.entity_type est None mais tool_name connu → fallback map."""
    before_hook = build_before_dispatch_hook()
    after_hook = build_after_dispatch_hook()

    class _State:
        account_id = uuid4()
        user_id = uuid4()
        agent_run_id = None

    class _Call:
        name = "update_company_profile"

    class _Result:
        status = "ok"
        entity_type = None
        entity_id = uuid4()

    captured = {}

    async def _spy(**kw: Any) -> None:
        captured.update(kw)

    async def _run() -> None:
        await before_hook(_Call(), _State())
        with patch(
            "app.agent.memory.entity_memory.update_entity_memory",
            side_effect=_spy,
        ):
            await after_hook(_Call(), _Result())
            await asyncio.sleep(0)

    asyncio.run(_run())
    assert captured.get("entity_type") == "Entreprise"
