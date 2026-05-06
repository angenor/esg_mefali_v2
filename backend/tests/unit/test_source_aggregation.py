"""F56 / T045 — Tests unit pour ``aggregate_thread_sources``.

Pas de DB réelle : on mocke la session SQLAlchemy.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock
from uuid import uuid4

import pytest

from app.services.source_aggregation import aggregate_thread_sources


def _mock_db_with_messages(messages: list[dict[str, Any]]) -> MagicMock:
    """Construit un mock SQLAlchemy retournant une liste prédéfinie."""
    db = MagicMock()
    chain = db.execute.return_value
    chain.mappings.return_value.all.return_value = messages
    return db


@pytest.mark.unit
def test_empty_thread_returns_empty_list() -> None:
    db = _mock_db_with_messages([])
    out = aggregate_thread_sources(db, uuid4())
    assert out == []


@pytest.mark.unit
def test_single_message_with_one_source() -> None:
    sid = str(uuid4())
    messages = [
        {
            "message_id": uuid4(),
            "msg_created_at": None,
            "sources": [
                {
                    "source_id": sid,
                    "title": "ADEME 2024",
                    "publisher": "ADEME",
                    "url": "https://x",
                    "citation_index": 1,
                }
            ],
        }
    ]
    db = _mock_db_with_messages(messages)
    out = aggregate_thread_sources(db, uuid4())
    assert len(out) == 1
    assert out[0]["source_id"] == sid
    assert out[0]["citation_index"] == 1


@pytest.mark.unit
def test_dedup_across_messages() -> None:
    sid_a = str(uuid4())
    sid_b = str(uuid4())
    messages = [
        {
            "message_id": uuid4(),
            "msg_created_at": None,
            "sources": [
                {"source_id": sid_a, "title": "A", "publisher": "x", "url": "y"},
                {"source_id": sid_b, "title": "B", "publisher": "x", "url": "y"},
            ],
        },
        {
            "message_id": uuid4(),
            "msg_created_at": None,
            "sources": [
                # Re-cite sid_a → ignoré
                {"source_id": sid_a, "title": "A", "publisher": "x", "url": "y"},
                # Mais on n'ajoute pas une 3e
            ],
        },
    ]
    db = _mock_db_with_messages(messages)
    out = aggregate_thread_sources(db, uuid4())
    assert len(out) == 2
    assert {s["source_id"] for s in out} == {sid_a, sid_b}


@pytest.mark.unit
def test_renumbering_first_apparition_order() -> None:
    sid_a = str(uuid4())
    sid_b = str(uuid4())
    sid_c = str(uuid4())
    messages = [
        {
            "message_id": uuid4(),
            "msg_created_at": None,
            "sources": [
                {"source_id": sid_b, "title": "B", "publisher": "x", "url": "y"},
            ],
        },
        {
            "message_id": uuid4(),
            "msg_created_at": None,
            "sources": [
                {"source_id": sid_a, "title": "A", "publisher": "x", "url": "y"},
                {"source_id": sid_c, "title": "C", "publisher": "x", "url": "y"},
            ],
        },
    ]
    db = _mock_db_with_messages(messages)
    out = aggregate_thread_sources(db, uuid4())
    assert [s["citation_index"] for s in out] == [1, 2, 3]
    assert [s["source_id"] for s in out] == [sid_b, sid_a, sid_c]


@pytest.mark.unit
def test_skips_invalid_source_entries() -> None:
    messages = [
        {
            "message_id": uuid4(),
            "msg_created_at": None,
            "sources": [
                "not-a-dict",
                {},  # missing source_id
                {"source_id": str(uuid4()), "title": "valid"},
            ],
        }
    ]
    db = _mock_db_with_messages(messages)
    out = aggregate_thread_sources(db, uuid4())
    assert len(out) == 1
