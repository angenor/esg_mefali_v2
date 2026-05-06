"""F54 / T060 — Tests unitaires admin_mode (US6, FR-018)."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agent.context.admin_mode import (
    is_mutation_tool_name,
    mark_mutation_tools_require_confirmation,
    render_admin_banner,
)
from app.agent.context.models import ToolRender


@pytest.mark.unit
class TestIsMutationToolName:
    @pytest.mark.parametrize(
        "name",
        [
            "create_project",
            "update_company_profile",
            "delete_attestation",
            "patch_indicateur",
            "submit_candidature",
            "set_score",
            "archive_projet",
        ],
    )
    def test_recognized_mutation(self, name: str) -> None:
        assert is_mutation_tool_name(name) is True

    @pytest.mark.parametrize(
        "name",
        [
            "ask_qcu",
            "ask_form",
            "show_chart",
            "search_source",
            "cite_source",
            "recall_history",
            "respond_user",
        ],
    )
    def test_recognized_non_mutation(self, name: str) -> None:
        assert is_mutation_tool_name(name) is False


@pytest.mark.unit
class TestMarkMutationTools:
    def test_only_mutation_tools_get_annotated(self) -> None:
        tools = [
            ToolRender(name="ask_qcu", use_when="Question fermée"),
            ToolRender(name="create_project", use_when="Créer un projet"),
            ToolRender(name="update_company_profile", use_when="Mettre à jour"),
            ToolRender(name="show_chart", use_when="Afficher graphique"),
        ]
        out = mark_mutation_tools_require_confirmation(tools)
        assert len(out) == 4
        # ask_qcu, show_chart : pas de marker.
        assert "[requires_confirmation]" not in out[0].use_when
        assert "[requires_confirmation]" in out[1].use_when
        assert "[requires_confirmation]" in out[2].use_when
        assert "[requires_confirmation]" not in out[3].use_when

    def test_idempotent(self) -> None:
        tools = [
            ToolRender(name="create_project", use_when="X [requires_confirmation]"),
        ]
        out = mark_mutation_tools_require_confirmation(tools)
        # Pas de double marker.
        assert out[0].use_when.count("[requires_confirmation]") == 1


@pytest.mark.unit
class TestRenderAdminBanner:
    def test_banner_contains_account_id(self) -> None:
        aid = uuid4()
        banner = render_admin_banner(aid)
        assert str(aid) in banner
        assert "MODE SUPPORT ADMIN" in banner

    def test_banner_mentions_confirmation(self) -> None:
        banner = render_admin_banner(uuid4())
        assert "confirmation" in banner.lower()

    def test_banner_mentions_audit(self) -> None:
        banner = render_admin_banner(uuid4())
        assert "audit" in banner.lower()

    def test_banner_with_none_account(self) -> None:
        banner = render_admin_banner(None)
        assert "compte non spécifié" in banner
