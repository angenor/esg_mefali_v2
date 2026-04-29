"""F18 — Tests d'exécution recall_history avec mocks de session SQL."""

from __future__ import annotations

from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.chat.memory.recall_history_tool import (
    RecallHistoryArgs,
    _fetch_recent_message_ids,
    execute_recall_history,
)


def _fake_db(recent_ids: list[str], hits: list[dict]) -> MagicMock:
    """Construit une session SQLAlchemy mockée avec deux résultats.

    Le premier ``db.execute(...).all()`` renvoie ``recent_ids``.
    Le second ``db.execute(...).mappings().all()`` renvoie ``hits``.
    """
    db = MagicMock()

    recent_result = MagicMock()
    recent_result.all.return_value = [(rid,) for rid in recent_ids]

    hits_result = MagicMock()
    hits_result.mappings.return_value.all.return_value = hits

    db.execute.side_effect = [recent_result, hits_result]
    return db


class TestExecuteRecallHistory:
    def test_returns_hits_when_query_ok(self) -> None:
        thread_id = uuid4()
        msg_id = uuid4()

        hits = [
            {
                "id": msg_id,
                "thread_id": thread_id,
                "role": "user",
                "content": "Discussion biogaz Sénégal",
                "payload_json": None,
                "created_at": datetime.now(tz=UTC),
                "similarity": 0.91,
            }
        ]
        db = _fake_db(recent_ids=[str(uuid4()) for _ in range(15)], hits=hits)

        with patch("app.embeddings_client.embed", return_value=[[0.1] * 1024]):
            out = execute_recall_history(
                db=db,
                account_id=uuid4(),
                thread_id=thread_id,
                args=RecallHistoryArgs(query="biogaz Sénégal", k=5),
            )

        assert len(out) == 1
        hit = out[0]
        assert hit.message_id == msg_id
        assert hit.thread_id == thread_id
        assert hit.role == "user"
        assert "biogaz" in hit.snippet.lower()
        assert 0.0 <= hit.similarity <= 1.0

    def test_no_recent_messages_still_works(self) -> None:
        thread_id = uuid4()
        db = _fake_db(recent_ids=[], hits=[])

        with patch("app.embeddings_client.embed", return_value=[[0.1] * 1024]):
            out = execute_recall_history(
                db=db,
                account_id=uuid4(),
                thread_id=thread_id,
                args=RecallHistoryArgs(query="biogaz Sénégal"),
            )
        assert out == []

    def test_payload_extracted_in_snippet(self) -> None:
        thread_id = uuid4()
        hits = [
            {
                "id": uuid4(),
                "thread_id": thread_id,
                "role": "assistant",
                "content": "",
                "payload_json": {"label": "Empreinte carbone projet biogaz"},
                "created_at": datetime.now(tz=UTC),
                "similarity": 0.8,
            }
        ]
        db = _fake_db(recent_ids=[], hits=hits)
        with patch("app.embeddings_client.embed", return_value=[[0.1] * 1024]):
            out = execute_recall_history(
                db=db,
                account_id=uuid4(),
                thread_id=thread_id,
                args=RecallHistoryArgs(query="biogaz Sénégal"),
            )
        assert out
        assert "Empreinte carbone" in out[0].snippet

    def test_voyage_returns_empty_vectors_returns_empty(self) -> None:
        with patch("app.embeddings_client.embed", return_value=[]):
            out = execute_recall_history(
                db=MagicMock(),
                account_id=uuid4(),
                thread_id=uuid4(),
                args=RecallHistoryArgs(query="biogaz Sénégal"),
            )
        assert out == []


class TestFetchRecentMessageIds:
    def test_returns_string_ids(self) -> None:
        db = MagicMock()
        result = MagicMock()
        result.all.return_value = [(uuid4(),) for _ in range(3)]
        db.execute.return_value = result

        ids = _fetch_recent_message_ids(
            db, thread_id=uuid4(), account_id=uuid4(), limit=15
        )
        assert len(ids) == 3
        assert all(isinstance(i, str) for i in ids)
