"""F03 US2 — Tests unitaires des LLM tools (validation des schémas Pydantic)."""

from __future__ import annotations

import uuid
from unittest.mock import MagicMock

import pytest
from pydantic import ValidationError

from app.schemas.source import (
    CiteSourceInput,
    FlagUnsourcedInput,
    SearchSourceInput,
)
from app.services.llm_tools import (
    handle_cite_source,
    handle_flag_unsourced,
    handle_search_source,
)


@pytest.mark.unit
class TestSchemasForbidExtra:
    def test_cite_source_extra_forbidden(self):
        with pytest.raises(ValidationError):
            CiteSourceInput.model_validate(
                {"source_id": str(uuid.uuid4()), "extra": "x"}
            )

    def test_search_source_extra_forbidden(self):
        with pytest.raises(ValidationError):
            SearchSourceInput.model_validate({"query": "x", "wrong": True})

    def test_search_source_query_min_length(self):
        with pytest.raises(ValidationError):
            SearchSourceInput.model_validate({"query": ""})

    def test_search_source_k_bounds(self):
        with pytest.raises(ValidationError):
            SearchSourceInput.model_validate({"query": "ok", "k": 0})
        with pytest.raises(ValidationError):
            SearchSourceInput.model_validate({"query": "ok", "k": 100})

    def test_flag_unsourced_claim_max_length(self):
        with pytest.raises(ValidationError):
            FlagUnsourcedInput.model_validate({"claim": "x" * 2001})


@pytest.mark.unit
class TestCiteSourceHandler:
    def test_returns_not_found_when_db_empty(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value.first.return_value = None
        out = handle_cite_source(
            db, CiteSourceInput(source_id=uuid.uuid4())
        )
        assert out.error == "not_found"
        assert out.source is None

    def test_returns_not_verified_when_pending(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value.first.return_value = {
            "id": uuid.uuid4(),
            "url": "https://x.example/a",
            "title": "A",
            "publisher": "GCF",
            "version": None,
            "date_publi": None,
            "page": None,
            "section": None,
            "captured_at": "2025-01-01T00:00:00Z",
            "verified_at": None,
            "verification_status": "pending",
            "notes": None,
        }
        out = handle_cite_source(db, CiteSourceInput(source_id=uuid.uuid4()))
        assert out.error == "not_verified"

    def test_returns_source_when_verified(self):
        db = MagicMock()
        sid = uuid.uuid4()
        db.execute.return_value.mappings.return_value.first.return_value = {
            "id": sid,
            "url": "https://x.example/a",
            "title": "A",
            "publisher": "GCF",
            "version": None,
            "date_publi": None,
            "page": None,
            "section": None,
            "captured_at": "2025-01-01T00:00:00+00:00",
            "verified_at": "2025-01-02T00:00:00+00:00",
            "verification_status": "verified",
            "notes": None,
        }
        out = handle_cite_source(db, CiteSourceInput(source_id=sid))
        assert out.source is not None
        assert out.source.verification_status.value == "verified"


@pytest.mark.unit
class TestSearchSourceHandler:
    def test_excludes_non_verified_via_sql(self):
        """L'exclusion repose sur la clause WHERE — on vérifie qu'elle est posée."""
        db = MagicMock()
        db.execute.return_value.mappings.return_value.all.return_value = []

        def emb(_):
            return [[0.0] * 1024]

        out = handle_search_source(
            db, SearchSourceInput(query="GCF"), embedding_func=emb
        )
        # Inspecte le SQL passé
        sql_str = str(db.execute.call_args[0][0])
        assert "verification_status = 'verified'" in sql_str
        assert out.items == []

    def test_falls_back_to_text_when_embedding_fails(self):
        db = MagicMock()
        db.execute.return_value.mappings.return_value.all.return_value = []

        def boom(_):
            raise RuntimeError("voyage down")

        out = handle_search_source(
            db, SearchSourceInput(query="GCF"), embedding_func=boom
        )
        assert out.items == []


@pytest.mark.unit
class TestFlagUnsourcedHandler:
    def test_returns_id(self):
        db = MagicMock()
        out = handle_flag_unsourced(
            db, FlagUnsourcedInput(claim="seuil GCF inconnu", context={"i": 1})
        )
        assert isinstance(out.id, uuid.UUID)
        # SQL appelé une fois
        assert db.execute.called
