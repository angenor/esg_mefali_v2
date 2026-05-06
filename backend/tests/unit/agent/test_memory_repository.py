"""F57 — Tests unit du module ``app.chat.memory.repository``.

Vérifie la construction des SQL queries (mock Session) et leur scope
``account_id`` + ``thread_id``.
"""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest

from app.chat.memory import repository

pytestmark = pytest.mark.unit


def test_get_thread_for_account_returns_dict_when_found() -> None:
    db = MagicMock()
    tid = uuid.uuid4()
    aid = uuid.uuid4()
    expected = {"id": tid, "summary": None, "last_compacted_at": None, "archived": False}

    mappings = MagicMock()
    mappings.first.return_value = expected
    result_proxy = MagicMock()
    result_proxy.mappings.return_value = mappings
    db.execute.return_value = result_proxy

    out = repository.get_thread_for_account(
        db, thread_id=tid, account_id=aid
    )
    assert out == expected


def test_get_thread_for_account_returns_none_when_missing() -> None:
    db = MagicMock()
    mappings = MagicMock()
    mappings.first.return_value = None
    result_proxy = MagicMock()
    result_proxy.mappings.return_value = mappings
    db.execute.return_value = result_proxy

    out = repository.get_thread_for_account(
        db, thread_id=uuid.uuid4(), account_id=uuid.uuid4()
    )
    assert out is None


def test_count_messages_default_no_compacted_filter() -> None:
    db = MagicMock()
    result_proxy = MagicMock()
    result_proxy.first.return_value = (12,)
    db.execute.return_value = result_proxy

    out = repository.count_messages(
        db, thread_id=uuid.uuid4(), account_id=uuid.uuid4()
    )
    assert out == 12
    sql_text = str(db.execute.call_args[0][0])
    assert "compacted = FALSE" not in sql_text


def test_count_messages_with_compacted_filter() -> None:
    db = MagicMock()
    result_proxy = MagicMock()
    result_proxy.first.return_value = (5,)
    db.execute.return_value = result_proxy

    out = repository.count_messages(
        db,
        thread_id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        only_non_compacted=True,
    )
    assert out == 5
    sql_text = str(db.execute.call_args[0][0])
    assert "compacted = FALSE" in sql_text


def test_count_messages_with_embedding() -> None:
    db = MagicMock()
    result_proxy = MagicMock()
    result_proxy.first.return_value = (8,)
    db.execute.return_value = result_proxy

    out = repository.count_messages_with_embedding(
        db, thread_id=uuid.uuid4(), account_id=uuid.uuid4()
    )
    assert out == 8


def test_get_entities_referenced_dedup() -> None:
    db = MagicMock()
    eid = uuid.uuid4()
    rows = [
        ("Entreprise", str(eid), "ACME"),
        ("Entreprise", str(eid), "ACME-alt"),  # duplicate
        ("Projet", str(uuid.uuid4()), "Solaire"),
        ("Bogus", str(uuid.uuid4()), "skip"),  # filtered out
    ]
    result_proxy = MagicMock()
    result_proxy.all.return_value = rows
    db.execute.return_value = result_proxy

    out = repository.get_entities_referenced(
        db, thread_id=uuid.uuid4(), account_id=uuid.uuid4()
    )
    assert len(out) == 2
    types = {e["type"] for e in out}
    assert types == {"Entreprise", "Projet"}


def test_purge_thread_embeddings_returns_count_before() -> None:
    db = MagicMock()
    # Use first().scalar() pattern... actually, the impl uses .scalar()
    db.execute.side_effect = [
        MagicMock(scalar=MagicMock(return_value=42)),  # SELECT COUNT
        MagicMock(),  # UPDATE
    ]
    out = repository.purge_thread_embeddings(
        db, thread_id=uuid.uuid4(), account_id=uuid.uuid4()
    )
    assert out == 42


def test_clear_thread_summary_returns_pre_state() -> None:
    db = MagicMock()
    result_proxy = MagicMock()
    result_proxy.first.return_value = (True, False)
    db.execute.side_effect = [result_proxy, MagicMock()]

    summary_was, comp_was = repository.clear_thread_summary(
        db, thread_id=uuid.uuid4(), account_id=uuid.uuid4()
    )
    assert summary_was is True
    assert comp_was is False


def test_clear_thread_summary_returns_false_false_when_thread_missing() -> None:
    db = MagicMock()
    result_proxy = MagicMock()
    result_proxy.first.return_value = None
    db.execute.return_value = result_proxy

    out = repository.clear_thread_summary(
        db, thread_id=uuid.uuid4(), account_id=uuid.uuid4()
    )
    assert out == (False, False)


def test_write_audit_memory_forget_returns_uuid() -> None:
    db = MagicMock()
    audit_id = repository.write_audit_memory_forget(
        db,
        thread_id=uuid.uuid4(),
        account_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        embeddings_purged=10,
        summary_was_set=True,
    )
    assert isinstance(audit_id, uuid.UUID)


def test_get_or_create_entity_memory_returns_dict_when_found() -> None:
    db = MagicMock()
    mappings = MagicMock()
    mappings.first.return_value = {"id": uuid.uuid4(), "version": 2}
    proxy = MagicMock()
    proxy.mappings.return_value = mappings
    db.execute.return_value = proxy

    out = repository.get_or_create_entity_memory(
        db,
        account_id=uuid.uuid4(),
        entity_type="Entreprise",
        entity_id=uuid.uuid4(),
    )
    assert out is not None and out["version"] == 2


def test_upsert_entity_memory_returns_id_and_version() -> None:
    db = MagicMock()
    new_id = uuid.uuid4()
    proxy = MagicMock()
    proxy.first.return_value = (new_id, 3)
    db.execute.return_value = proxy

    out_id, out_version = repository.upsert_entity_memory(
        db,
        account_id=uuid.uuid4(),
        entity_type="Projet",
        entity_id=uuid.uuid4(),
        summary="bullet",
        sources_used=[],
    )
    assert out_id == new_id
    assert out_version == 3


def test_delete_entity_memory_returns_rowcount() -> None:
    db = MagicMock()
    proxy = MagicMock()
    proxy.rowcount = 1
    db.execute.return_value = proxy

    deleted = repository.delete_entity_memory(
        db,
        account_id=uuid.uuid4(),
        entity_type="Projet",
        entity_id=uuid.uuid4(),
    )
    assert deleted == 1


def test_write_audit_entity_memory_returns_uuid() -> None:
    db = MagicMock()
    audit_id = repository.write_audit_entity_memory(
        db,
        account_id=uuid.uuid4(),
        entity_type="Entreprise",
        entity_id=uuid.uuid4(),
        user_id=uuid.uuid4(),
        operation="upsert",
        version=1,
    )
    assert isinstance(audit_id, uuid.UUID)
