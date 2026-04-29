"""F18 — Tests des helpers privés de context_builder (couverture ciblée)."""

from __future__ import annotations

import sys
from datetime import UTC, datetime
from unittest.mock import MagicMock, patch
from uuid import uuid4

from app.chat.memory import context_builder as cb


class TestRowToDict:
    def test_dict_passthrough(self) -> None:
        assert cb._row_to_dict({"a": 1}) == {"a": 1}

    def test_namedtuple_asdict(self) -> None:
        from collections import namedtuple

        Row = namedtuple("Row", "a b")
        assert cb._row_to_dict(Row(1, 2)) == {"a": 1, "b": 2}

    def test_object_with_dict(self) -> None:
        class Row:
            def __init__(self):
                self.x = 1
                self._private = "hidden"

        out = cb._row_to_dict(Row())
        assert out == {"x": 1}

    def test_unknown_returns_empty(self) -> None:
        assert cb._row_to_dict(42) == {}


class TestTruncateContent:
    def test_short_passthrough(self) -> None:
        assert cb._truncate_content("hi") == "hi"

    def test_none_returns_empty(self) -> None:
        assert cb._truncate_content(None) == ""

    def test_long_truncated_with_marker(self) -> None:
        s = "x" * (cb.MAX_MESSAGE_CONTENT_CHARS + 100)
        out = cb._truncate_content(s)
        assert out.endswith("[…tronqué…]")
        assert len(out) <= cb.MAX_MESSAGE_CONTENT_CHARS


class TestBuildMessageView:
    def test_returns_none_for_system_role(self) -> None:
        assert cb._build_message_view({"role": "system", "content": "x"}) is None

    def test_returns_none_for_unknown_role(self) -> None:
        assert cb._build_message_view({"role": "tool", "content": "x"}) is None

    def test_uses_default_created_at_when_missing(self) -> None:
        view = cb._build_message_view({"role": "user", "content": "hi"})
        assert view is not None
        assert view.created_at is not None

    def test_extracts_payload_label(self) -> None:
        view = cb._build_message_view(
            {
                "role": "assistant",
                "content": "",
                "payload_json": {"label": "Pie chart"},
                "created_at": datetime.now(tz=UTC),
            }
        )
        assert view is not None
        assert view.payload_label == "Pie chart"


class TestFormatMoney:
    def test_money_dict(self) -> None:
        assert cb._format_money({"amount": 100, "currency": "XOF"}) == "100 XOF"

    def test_money_no_currency(self) -> None:
        assert cb._format_money({"amount": 100, "currency": None}) == "100"

    def test_str_fallback(self) -> None:
        assert cb._format_money(42) == "42"


class TestRenderProfileSection:
    def test_returns_none_for_empty(self) -> None:
        assert cb._render_profile_section(None) is None
        assert cb._render_profile_section({}) is None

    def test_renders_full_profile(self) -> None:
        profile = {
            "raison_sociale": "Acme",
            "forme_juridique": "SARL",
            "secteur_activite": "Énergie",
            "pays": "Sénégal",
            "ville": "Dakar",
            "annee_creation": 2018,
            "effectif_total": 24,
            "chiffre_affaires": {"amount": 100, "currency": "XOF"},
            "description_activite": "Biogaz",
            "indicateurs_esg_synthetiques": {"co2": 10},
        }
        out = cb._render_profile_section(profile)
        assert out is not None
        for needle in (
            "Acme",
            "SARL",
            "Énergie",
            "Sénégal / Dakar",
            "2018",
            "24 salariés",
            "100 XOF",
            "Biogaz",
        ):
            assert needle in out

    def test_pays_only_without_ville(self) -> None:
        out = cb._render_profile_section(
            {"raison_sociale": "X", "pays": "Sénégal"}
        )
        assert out is not None
        assert "Pays : Sénégal" in out


class TestRenderProjectsSection:
    def test_returns_none_for_empty(self) -> None:
        assert cb._render_projects_section([]) is None

    def test_renders_projects(self) -> None:
        out = cb._render_projects_section(
            [
                {
                    "id": "p-1",
                    "nom": "Biogaz",
                    "statut": "actif",
                    "secteur": "Énergie",
                    "pays": "SN",
                    "montant_total": {"amount": 100, "currency": "XOF"},
                    "description": "Description courte",
                }
            ]
        )
        assert out is not None
        assert "Biogaz" in out
        assert "actif" in out
        assert "100 XOF" in out
        assert "Description courte" in out

    def test_falls_back_to_id_when_nom_missing(self) -> None:
        out = cb._render_projects_section([{"id": "fallback-id"}])
        assert out is not None
        assert "fallback-id" in out


class TestRenderMessagesSection:
    def test_returns_none_for_empty(self) -> None:
        assert cb._render_messages_section([]) is None

    def test_payload_only(self) -> None:
        out = cb._render_messages_section(
            [{"role": "assistant", "content": "", "payload_label": "Bar chart"}]
        )
        assert out is not None
        assert "(payload) Bar chart" in out

    def test_content_with_payload(self) -> None:
        out = cb._render_messages_section(
            [
                {
                    "role": "assistant",
                    "content": "Voici le graphique",
                    "payload_label": "Bar chart",
                }
            ]
        )
        assert out is not None
        assert "Voici le graphique" in out
        assert "(payload) Bar chart" in out


class TestRebuildViews:
    def test_returns_all_when_target_ge_len(self) -> None:
        from app.chat.memory.context_builder import ChatMessageView, _rebuild_views

        views = (
            ChatMessageView(
                role="user",
                content="x",
                payload_label=None,
                created_at=datetime.now(tz=UTC),
            ),
        )
        assert _rebuild_views(views, 5) == views

    def test_keeps_last_n(self) -> None:
        from app.chat.memory.context_builder import ChatMessageView, _rebuild_views

        views = tuple(
            ChatMessageView(
                role="user",
                content=f"m{i}",
                payload_label=None,
                created_at=datetime.now(tz=UTC),
            )
            for i in range(5)
        )
        out = _rebuild_views(views, 2)
        assert len(out) == 2
        assert out[-1].content == "m4"


class TestResolveBudget:
    def test_default_when_no_config(self, monkeypatch) -> None:
        monkeypatch.delenv("CONTEXT_TOKEN_BUDGET", raising=False)
        with patch("app.config.get_settings", side_effect=Exception("no env")):
            assert cb._resolve_budget() == cb.DEFAULT_TOKEN_BUDGET

    def test_env_var(self, monkeypatch) -> None:
        monkeypatch.setenv("CONTEXT_TOKEN_BUDGET", "777")
        with patch("app.config.get_settings", side_effect=Exception("no env")):
            assert cb._resolve_budget() == 777

    def test_invalid_env_falls_back(self, monkeypatch) -> None:
        monkeypatch.setenv("CONTEXT_TOKEN_BUDGET", "not_an_int")
        with patch("app.config.get_settings", side_effect=Exception("no env")):
            assert cb._resolve_budget() == cb.DEFAULT_TOKEN_BUDGET


class TestReadProfileFallbacks:
    def test_returns_none_when_module_import_fails(self) -> None:
        original = sys.modules.get("app.entreprise")
        sys.modules["app.entreprise"] = None  # type: ignore[assignment]
        try:
            out = cb._read_profile(MagicMock(), uuid4())
            assert out is None
        finally:
            if original is not None:
                sys.modules["app.entreprise"] = original
            else:
                sys.modules.pop("app.entreprise", None)

    def test_returns_none_when_select_one_returns_none(self) -> None:
        with patch(
            "app.entreprise.service._select_one", return_value=None
        ):
            assert cb._read_profile(MagicMock(), uuid4()) is None


class TestReadProjetsFallbacks:
    def test_returns_empty_when_service_raises(self) -> None:
        with patch(
            "app.projets.service.list_projets",
            side_effect=RuntimeError("DB down"),
        ):
            assert cb._read_projets(MagicMock(), uuid4()) == []


class TestReadRecentMessagesFallback:
    def test_uses_count_when_available(self) -> None:
        with (
            patch(
                "app.chat.repository.list_recent_messages",
                return_value=[{"role": "user", "content": "hi"}],
            ),
            patch(
                "app.chat.repository.count_messages_in_thread",
                return_value=42,
            ),
        ):
            recent, total = cb._read_recent_messages(
                MagicMock(), thread_id=uuid4(), account_id=uuid4(), limit=15
            )
            assert total == 42
            assert len(recent) == 1
