"""F18 — Tests unitaires du context_builder (mocks repos F11/F12/F13)."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any
from unittest.mock import patch
from uuid import uuid4

import pytest

from app.chat.memory import context_builder as cb
from app.chat.memory.context_builder import (
    DEFAULT_RECENT_LIMIT,
    RECALL_HISTORY_THRESHOLD,
    ChatMessageView,
    ContextBundle,
    build_context,
    render_bundle,
)


def _msg(
    role: str,
    content: str,
    minutes_ago: int = 0,
    payload_json: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "id": uuid4(),
        "role": role,
        "content": content,
        "payload_json": payload_json,
        "created_at": datetime.now(tz=UTC) - timedelta(minutes=minutes_ago),
    }


@pytest.fixture
def patched_io():
    """Patche les helpers de lecture pour éviter toute dépendance DB."""
    state: dict[str, Any] = {
        "profile": None,
        "projets": [],
        "messages": [],
        "total": 0,
    }

    def fake_read_profile(db, account_id):
        return state["profile"]

    def fake_read_projets(db, account_id):
        return list(state["projets"])

    def fake_read_recent(db, *, thread_id, account_id, limit):
        return list(state["messages"])[-limit:], state["total"]

    with (
        patch.object(cb, "_read_profile", side_effect=fake_read_profile),
        patch.object(cb, "_read_projets", side_effect=fake_read_projets),
        patch.object(cb, "_read_recent_messages", side_effect=fake_read_recent),
    ):
        yield state


# --- build_context : scénarios -----------------------------------------


class TestBuildContext:
    def test_empty_state_returns_minimal_bundle(self, patched_io) -> None:
        bundle = build_context(
            db=None, account_id=uuid4(), thread_id=uuid4(), token_budget=2000
        )
        assert isinstance(bundle, ContextBundle)
        assert bundle.profile is None
        assert bundle.projets == ()
        assert bundle.recent_messages == ()
        assert bundle.expose_recall_history is False
        assert bundle.estimated_tokens == 0

    def test_profile_only(self, patched_io) -> None:
        patched_io["profile"] = {
            "raison_sociale": "Acme",
            "secteur_activite": "Énergie",
        }
        bundle = build_context(
            db=None, account_id=uuid4(), thread_id=uuid4(), token_budget=2000
        )
        assert bundle.profile is not None
        rendered = bundle.to_system_message()
        assert "Acme" in rendered
        assert "# Profil entreprise" in rendered
        assert "# Projets actifs" not in rendered

    def test_projects_filtered_active_only(self, patched_io) -> None:
        patched_io["projets"] = [
            {"id": "a", "nom": "P1", "statut": "actif"},
            {"id": "b", "nom": "P2", "statut": "cloture"},
            {"id": "c", "nom": "P3", "statut": "en_cours"},
        ]
        bundle = build_context(
            db=None, account_id=uuid4(), thread_id=uuid4(), token_budget=2000
        )
        names = [p.get("nom") for p in bundle.projets]
        assert "P1" in names and "P3" in names
        assert "P2" not in names

    def test_window_15_chronological_order(self, patched_io) -> None:
        msgs = [
            _msg("user" if i % 2 else "assistant", f"msg-{i}", minutes_ago=20 - i)
            for i in range(20)
        ]
        patched_io["messages"] = msgs
        patched_io["total"] = 20

        bundle = build_context(
            db=None,
            account_id=uuid4(),
            thread_id=uuid4(),
            token_budget=10_000,
        )
        assert len(bundle.recent_messages) <= DEFAULT_RECENT_LIMIT
        ts = [m.created_at for m in bundle.recent_messages]
        assert ts == sorted(ts)

    def test_expose_recall_flag_above_threshold(self, patched_io) -> None:
        patched_io["messages"] = [_msg("user", "hi", minutes_ago=i) for i in range(5)]
        patched_io["total"] = RECALL_HISTORY_THRESHOLD + 1
        bundle = build_context(
            db=None, account_id=uuid4(), thread_id=uuid4(), token_budget=2000
        )
        assert bundle.expose_recall_history is True

    def test_expose_recall_flag_below_threshold(self, patched_io) -> None:
        patched_io["total"] = RECALL_HISTORY_THRESHOLD
        bundle = build_context(
            db=None, account_id=uuid4(), thread_id=uuid4(), token_budget=2000
        )
        assert bundle.expose_recall_history is False

    def test_no_sensitive_fields_leak(self, patched_io) -> None:
        patched_io["profile"] = {
            "raison_sociale": "Acme",
            "password": "should_not_appear",
            "jwt": "leak_token",
            "refresh_token": "secret",
        }
        bundle = build_context(
            db=None, account_id=uuid4(), thread_id=uuid4(), token_budget=2000
        )
        rendered = bundle.to_system_message()
        assert "should_not_appear" not in rendered
        assert "leak_token" not in rendered
        assert "secret" not in rendered

    def test_freshness_no_cache_between_calls(self, patched_io) -> None:
        patched_io["profile"] = {"raison_sociale": "Acme", "effectif_total": 10}
        first = build_context(
            db=None, account_id=uuid4(), thread_id=uuid4(), token_budget=2000
        )
        assert first.profile is not None
        assert first.profile["effectif_total"] == 10

        # Mutation intermédiaire (US6)
        patched_io["profile"]["effectif_total"] = 42

        second = build_context(
            db=None, account_id=uuid4(), thread_id=uuid4(), token_budget=2000
        )
        assert second.profile is not None
        assert second.profile["effectif_total"] == 42

    def test_budget_compaction(self, patched_io) -> None:
        patched_io["projets"] = [
            {
                "id": f"p-{i}",
                "nom": f"Projet {i}",
                "statut": "actif",
                "description": "x" * 2000,
            }
            for i in range(25)
        ]
        bundle = build_context(
            db=None, account_id=uuid4(), thread_id=uuid4(), token_budget=400
        )
        assert bundle.estimated_tokens <= 400
        assert len(bundle.projets) <= 10

    def test_payload_label_extracted_for_message_view(self, patched_io) -> None:
        patched_io["messages"] = [
            _msg(
                "assistant",
                "",
                payload_json={"label": "Graphique CA annuel"},
                minutes_ago=1,
            )
        ]
        patched_io["total"] = 1
        bundle = build_context(
            db=None, account_id=uuid4(), thread_id=uuid4(), token_budget=2000
        )
        assert bundle.recent_messages
        view = bundle.recent_messages[0]
        assert isinstance(view, ChatMessageView)
        assert view.payload_label == "Graphique CA annuel"


# --- render_bundle : scénarios -----------------------------------------


class TestRenderBundle:
    def test_omits_empty_sections(self) -> None:
        assert render_bundle(None, [], []) == ""

    def test_renders_profile_only(self) -> None:
        out = render_bundle({"raison_sociale": "Acme"}, [], [])
        assert "# Profil entreprise" in out
        assert "Acme" in out
        assert "# Projets actifs" not in out
        assert "# Conversation récente" not in out

    def test_renders_money_format(self) -> None:
        out = render_bundle(
            {
                "raison_sociale": "Acme",
                "chiffre_affaires": {"amount": "850000", "currency": "XOF"},
            },
            [],
            [],
        )
        assert "850000 XOF" in out

    def test_renders_messages_chronologically(self) -> None:
        out = render_bundle(
            None,
            [],
            [
                {"role": "user", "content": "Bonjour"},
                {"role": "assistant", "content": "Salut !"},
            ],
        )
        assert "# Conversation récente" in out
        assert out.index("Bonjour") < out.index("Salut")

    def test_payload_label_with_empty_content(self) -> None:
        out = render_bundle(
            None,
            [],
            [{"role": "assistant", "content": "", "payload_label": "Pie chart"}],
        )
        assert "Pie chart" in out
        assert "(payload)" in out
