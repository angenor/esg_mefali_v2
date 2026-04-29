"""F18 — Tests unitaires du tool ``recall_history``.

Couvre :

- la validation du schéma Pydantic strict (extra='forbid'),
- le court-circuit des queries < 3 chars (FR-016),
- l'enregistrement idempotent dans le tool_registry (F14),
- le snippet et l'extraction de label.

Les tests d'intégration pgvector (recherche cosinus, isolation RLS,
gating > 15 messages) sont reportés à un environnement DB.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.chat.memory.recall_history_tool import (
    DEFAULT_K,
    MAX_K,
    RecallHistoryArgs,
    _make_snippet,
    execute_recall_history,
)

# --- Schéma Pydantic strict --------------------------------------------


class TestRecallHistoryArgs:
    def test_defaults(self) -> None:
        args = RecallHistoryArgs(query="biogaz Sénégal")
        assert args.k == DEFAULT_K

    def test_extra_keys_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            RecallHistoryArgs(query="hello", k=3, foo="bar")  # type: ignore[call-arg]

    def test_query_required_min_length(self) -> None:
        with pytest.raises(ValidationError):
            RecallHistoryArgs(query="")

    def test_k_bounds(self) -> None:
        RecallHistoryArgs(query="hi", k=1)
        RecallHistoryArgs(query="hi", k=MAX_K)
        with pytest.raises(ValidationError):
            RecallHistoryArgs(query="hi", k=0)
        with pytest.raises(ValidationError):
            RecallHistoryArgs(query="hi", k=MAX_K + 1)


# --- _make_snippet -----------------------------------------------------


class TestMakeSnippet:
    def test_uses_content_when_no_payload(self) -> None:
        out = _make_snippet("Bonjour le monde", None)
        assert out == "Bonjour le monde"

    def test_uses_payload_label_for_tool_messages(self) -> None:
        out = _make_snippet("", {"label": "Empreinte carbone"})
        assert "Empreinte carbone" in out

    def test_truncates_long_content(self) -> None:
        long = "a" * 1000
        out = _make_snippet(long, None)
        assert len(out) <= 240
        assert out.endswith("…")


# --- execute_recall_history : court-circuit --------------------------


class TestExecuteShortQuery:
    def test_short_query_returns_empty_list(self) -> None:
        out = execute_recall_history(
            db=MagicMock(),
            account_id=uuid4(),
            thread_id=uuid4(),
            args=RecallHistoryArgs(query="ab"),
        )
        assert out == []

    def test_short_query_does_not_call_voyage(self) -> None:
        with patch("app.embeddings_client.embed") as fake_embed:
            execute_recall_history(
                db=MagicMock(),
                account_id=uuid4(),
                thread_id=uuid4(),
                args=RecallHistoryArgs(query="ab"),
            )
            fake_embed.assert_not_called()

    def test_voyage_failure_returns_empty_safely(self) -> None:
        # Si embed lève, le tool ne propage pas — il retourne juste [].
        with patch(
            "app.embeddings_client.embed",
            side_effect=RuntimeError("voyage down"),
        ):
            out = execute_recall_history(
                db=MagicMock(),
                account_id=uuid4(),
                thread_id=uuid4(),
                args=RecallHistoryArgs(query="biogaz Sénégal"),
            )
            assert out == []


# --- Enregistrement registry F14 -------------------------------------


class TestToolRegistration:
    def test_tool_registered_in_registry(self) -> None:
        # L'import du module recall_history_tool a déjà déclenché
        # _register_tool() via le import side-effect.
        from app.orchestrator import tool_registry as registry

        assert "recall_history" in registry.TOOL_REGISTRY
        tool_def = registry.TOOL_REGISTRY["recall_history"]
        assert tool_def.schema is RecallHistoryArgs
        assert tool_def.use_when
        assert tool_def.dont_use_when

    def test_registration_is_idempotent(self) -> None:
        from app.chat.memory import recall_history_tool

        # _register_tool() est silencieux si déjà présent
        recall_history_tool._register_tool()
        recall_history_tool._register_tool()
        from app.orchestrator import tool_registry as registry

        assert "recall_history" in registry.TOOL_REGISTRY
