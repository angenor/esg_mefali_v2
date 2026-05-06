"""F57 / US7 — Tests unit deep pour entity_memory (UPSERT path)."""

from __future__ import annotations

import asyncio
from typing import Any
from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest

from app.agent.memory import entity_memory

pytestmark = pytest.mark.unit


def _stub_session(*, entity_exists_row: bool = True, snapshot_row=None) -> Any:
    sess = MagicMock()
    sess.commit.return_value = None
    sess.rollback.return_value = None
    sess.close.return_value = None

    # The SessionLocal call returns this stub. Each `execute()` call on it
    # returns a result that is either:
    #  - For SET LOCAL : not used (just returns None)
    #  - For SELECT 1 (entity exists check) : .first() returns row or None
    #  - For SELECT * (snapshot) : .mappings().first() returns row dict
    proxy_select_1 = MagicMock()
    proxy_select_1.first.return_value = (1,) if entity_exists_row else None

    proxy_snapshot = MagicMock()
    mappings = MagicMock()
    mappings.first.return_value = snapshot_row
    proxy_snapshot.mappings.return_value = mappings

    sess.execute.side_effect = [
        None,  # SET LOCAL app.current_account_id
        proxy_select_1,  # entity exists check
        proxy_snapshot,  # snapshot load
    ]
    return sess


def test_entity_exists_returns_false_for_unknown_table() -> None:
    sess = MagicMock()
    out = entity_memory._entity_exists(
        sess,
        entity_type="Bogus",  # type: ignore[arg-type]
        entity_id=uuid4(),
        account_id=uuid4(),
    )
    assert out is False


def test_entity_exists_returns_false_when_db_errors() -> None:
    sess = MagicMock()
    sess.execute.side_effect = RuntimeError("DB down")
    out = entity_memory._entity_exists(
        sess,
        entity_type="Entreprise",
        entity_id=uuid4(),
        account_id=uuid4(),
    )
    assert out is False


def test_entity_exists_returns_true_when_row_exists() -> None:
    sess = MagicMock()
    proxy = MagicMock()
    proxy.first.return_value = (1,)
    sess.execute.return_value = proxy
    out = entity_memory._entity_exists(
        sess,
        entity_type="Entreprise",
        entity_id=uuid4(),
        account_id=uuid4(),
    )
    assert out is True


def test_load_entity_snapshot_returns_dict_for_known_table() -> None:
    sess = MagicMock()
    proxy = MagicMock()
    mappings = MagicMock()
    mappings.first.return_value = {
        "id": uuid4(),
        "name": "ACME",
        "secteur": "C10.71",
    }
    proxy.mappings.return_value = mappings
    sess.execute.return_value = proxy
    snap = entity_memory._load_entity_snapshot(
        sess,
        entity_type="Entreprise",
        entity_id=uuid4(),
        account_id=uuid4(),
    )
    assert "name" in snap


def test_load_entity_snapshot_returns_empty_for_unknown_table() -> None:
    sess = MagicMock()
    out = entity_memory._load_entity_snapshot(
        sess,
        entity_type="Bogus",  # type: ignore[arg-type]
        entity_id=uuid4(),
        account_id=uuid4(),
    )
    assert out == {}


def test_build_entity_summary_prompt_contains_type_and_snapshot() -> None:
    sys_p, user_p = entity_memory._build_entity_summary_prompt(
        entity_type="Entreprise", snapshot={"name": "ACME"}
    )
    assert "Entreprise" in user_p
    assert "ACME" in user_p
    assert "factuel" in sys_p.lower() or "tu rédiges" in sys_p.lower()


def test_llm_summarize_returns_none_when_llm_down(monkeypatch) -> None:
    """LLM exception → log warning + None."""
    from app.agent.memory import entity_memory as em

    class _Boom:
        @property
        def chat(self):  # noqa: ANN201
            raise RuntimeError("LLM down")

    monkeypatch.setattr("app.llm_client.get_llm_client", lambda: _Boom())
    out = em._llm_summarize_entity(entity_type="Entreprise", snapshot={})
    assert out is None


def test_update_entity_memory_purge_path_full() -> None:
    """purge=True → DELETE + audit ; pas de LLM call."""
    aid = uuid4()
    eid = uuid4()
    sess = MagicMock()
    sess.commit.return_value = None
    sess.rollback.return_value = None
    sess.close.return_value = None

    import app.db as _db

    with patch.object(_db, "SessionLocal", return_value=sess), patch.object(
        entity_memory, "delete_entity_memory", return_value=1
    ) as mock_del, patch.object(
        entity_memory, "write_audit_entity_memory", return_value=uuid4()
    ) as mock_audit, patch.object(
        entity_memory, "_llm_summarize_entity"
    ) as mock_llm:
        asyncio.run(
            entity_memory.update_entity_memory(
                account_id=aid, entity_type="Projet", entity_id=eid, purge=True
            )
        )
    mock_del.assert_called_once()
    mock_audit.assert_called_once()
    mock_llm.assert_not_called()


def test_update_entity_memory_when_entity_missing_deletes() -> None:
    """Si l'entité business n'existe plus → DELETE entity_memory."""
    aid = uuid4()
    eid = uuid4()
    sess = MagicMock()
    sess.commit.return_value = None
    sess.rollback.return_value = None
    sess.close.return_value = None

    import app.db as _db

    with patch.object(_db, "SessionLocal", return_value=sess), patch.object(
        entity_memory, "_entity_exists", return_value=False
    ), patch.object(
        entity_memory, "delete_entity_memory", return_value=1
    ) as mock_del, patch.object(
        entity_memory, "write_audit_entity_memory", return_value=uuid4()
    ):
        asyncio.run(
            entity_memory.update_entity_memory(
                account_id=aid,
                entity_type="Entreprise",
                entity_id=eid,
            )
        )
    mock_del.assert_called_once()


def test_update_entity_memory_upsert_path_when_llm_ok() -> None:
    aid = uuid4()
    eid = uuid4()
    sess = MagicMock()
    sess.commit.return_value = None
    sess.rollback.return_value = None
    sess.close.return_value = None

    import app.db as _db

    with patch.object(_db, "SessionLocal", return_value=sess), patch.object(
        entity_memory, "_entity_exists", return_value=True
    ), patch.object(
        entity_memory, "_load_entity_snapshot", return_value={"name": "ACME"}
    ), patch.object(
        entity_memory,
        "_llm_summarize_entity",
        return_value="- bullet 1\n- bullet 2",
    ), patch.object(
        entity_memory, "upsert_entity_memory", return_value=(uuid4(), 2)
    ) as mock_up, patch.object(
        entity_memory, "write_audit_entity_memory", return_value=uuid4()
    ) as mock_audit:
        asyncio.run(
            entity_memory.update_entity_memory(
                account_id=aid,
                entity_type="Entreprise",
                entity_id=eid,
            )
        )
    mock_up.assert_called_once()
    mock_audit.assert_called_once()


def test_update_entity_memory_skips_when_llm_returns_none() -> None:
    """LLM down → on abandonne (retry au prochain trigger)."""
    aid = uuid4()
    eid = uuid4()
    sess = MagicMock()
    sess.commit.return_value = None
    sess.rollback.return_value = None
    sess.close.return_value = None

    import app.db as _db

    with patch.object(_db, "SessionLocal", return_value=sess), patch.object(
        entity_memory, "_entity_exists", return_value=True
    ), patch.object(
        entity_memory, "_load_entity_snapshot", return_value={}
    ), patch.object(
        entity_memory, "_llm_summarize_entity", return_value=None
    ), patch.object(
        entity_memory, "upsert_entity_memory"
    ) as mock_up:
        asyncio.run(
            entity_memory.update_entity_memory(
                account_id=aid,
                entity_type="Entreprise",
                entity_id=eid,
            )
        )
    mock_up.assert_not_called()
