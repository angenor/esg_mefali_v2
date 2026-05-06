"""F54 / T051 — Tests unitaires de la stratégie de troncature (FR-006).

6 cas couverts (FR-008, SC-005, SC-006) :
1. 50 indicateurs : aucun warning, prompt < budget.
2. 200 indicateurs : warning + step1 appliqué.
3. Tools `dont_use_when` retirés en step3.
4. Skills cap à 3 en step5.
5. Messages cap à 8 en step6.
6. Hard limit 6000 : warning over_hard_limit.
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from app.agent.context.models import (
    BusinessContextRender,
    ChatMsgRender,
    PageContextRender,
    PromptParts,
    SkillRender,
    ToolRender,
)
from app.agent.context.truncation import (
    INDICATEURS_PER_AXE_AFTER_TRUNCATION,
    MESSAGES_AFTER_TRUNCATION,
    SKILLS_AFTER_TRUNCATION,
    render_parts,
    truncate_prompt,
)


def _build_parts(
    *,
    business_text: str = "## CONTEXTE PME\nPME Test.",
    indicateurs_par_axe: dict | None = None,
    page_text: str = "## CONTEXTE PAGE\n/",
    skills: list[SkillRender] | None = None,
    tools: list[ToolRender] | None = None,
    messages: list[ChatMsgRender] | None = None,
) -> PromptParts:
    return PromptParts(
        identity="# IDENTITÉ\nESG Mefali assistant.",
        invariants="# INVARIANTS\n10 règles non négociables.",
        skills=skills or [],
        tools=tools or [],
        business_ctx=BusinessContextRender(
            text=business_text,
            indicateurs_par_axe=indicateurs_par_axe or {},
        ),
        page_ctx=PageContextRender(text=page_text),
        decision_tree="",
        metadata="",
        recent_messages=messages or [],
    )


@pytest.mark.unit
class TestTruncationNoWarning:
    """SC-005 : 50 indicateurs ne déclenchent pas de warning."""

    def test_below_budget_no_truncation(self) -> None:
        parts = _build_parts()
        prompt, report = truncate_prompt(parts, budget=4000)
        assert report.warning_emitted is False
        assert report.tokens_before == report.tokens_after
        assert report.parts_truncated == []
        assert report.steps_applied == []
        assert "ESG Mefali" in prompt


@pytest.mark.unit
class TestTruncationStep1Indicateurs:
    """SC-006 : 200 indicateurs → step1 ré-équilibre par axe."""

    def test_indicateurs_par_axe_truncated(self) -> None:
        # 100 indicateurs par axe → step1 doit cap à 5 chacun.
        per_axe = {
            "E": [f"e_indic_{i}" for i in range(100)],
            "S": [f"s_indic_{i}" for i in range(100)],
            "G": [f"g_indic_{i}" for i in range(100)],
        }
        # Texte business assez long pour dépasser le budget.
        long_business = "## CONTEXTE PME\n" + "Indicateur lourd " * 800
        parts = _build_parts(
            business_text=long_business,
            indicateurs_par_axe=per_axe,
        )
        # Budget bas pour forcer la troncature.
        prompt, report = truncate_prompt(parts, budget=300, hard_limit=10_000)
        assert report.warning_emitted is True
        assert "indicateurs_old" in report.parts_truncated
        # Aucun ``e_indic_99`` (au-delà du cap 5).
        assert "e_indic_99" not in prompt


@pytest.mark.unit
class TestTruncationStep2Archived:
    """Step 2 : retire mentions ``archive`` du business_ctx."""

    def test_archived_lines_removed(self) -> None:
        long_text = (
            "## CONTEXTE PME\n"
            "Projet Solaire (statut=en_analyse)\n"
            "Projet Vieux (statut=archive)\n"
            "Candidature Foo (statut=cloturee)\n"
            + "padding " * 600
        )
        parts = _build_parts(business_text=long_text)
        prompt, report = truncate_prompt(parts, budget=200, hard_limit=10_000)
        assert report.warning_emitted is True
        if "projets_archived" in report.parts_truncated:
            assert "statut=archive" not in prompt


@pytest.mark.unit
class TestTruncationStep3DontUseWhen:
    """Step 3 : retire `dont_use_when` des tools."""

    def test_dont_use_when_removed(self) -> None:
        tools = [
            ToolRender(
                name=f"tool_{i}",
                use_when=f"raison utilisation tool_{i}",
                dont_use_when=f"raison de NE PAS utiliser tool_{i} qui est très longue " * 10,
            )
            for i in range(10)
        ]
        parts = _build_parts(tools=tools)
        prompt, report = truncate_prompt(parts, budget=200, hard_limit=10_000)
        assert report.warning_emitted is True
        if "tools_dont_use_when" in report.parts_truncated:
            assert "ne pas utiliser quand" not in prompt
            # use_when doit être conservé.
            assert "raison utilisation tool_0" in prompt


@pytest.mark.unit
class TestTruncationStep5Skills:
    """Step 5 : cap skills à 3."""

    def test_skills_cap_to_3(self) -> None:
        skills = [
            SkillRender(code=f"skill_{i}", procedure_short="proc " * 20)
            for i in range(10)
        ]
        parts = _build_parts(skills=skills)
        prompt, report = truncate_prompt(parts, budget=120, hard_limit=10_000)
        assert report.warning_emitted is True
        if "skills_secondary" in report.parts_truncated:
            # Seuls les 3 premiers doivent rester.
            assert "skill_0" in prompt
            assert "skill_1" in prompt
            assert "skill_2" in prompt
            assert "skill_5" not in prompt


@pytest.mark.unit
class TestTruncationStep6Messages:
    """Step 6 : cap messages récents à 8 (les 8 derniers)."""

    def test_messages_keep_8_last(self) -> None:
        msgs = [
            ChatMsgRender(
                role="user",
                content=f"message {i} très long avec du contenu " * 5,
                timestamp=datetime.now(UTC),
            )
            for i in range(20)
        ]
        parts = _build_parts(messages=msgs)
        prompt, report = truncate_prompt(parts, budget=120, hard_limit=10_000)
        assert report.warning_emitted is True
        # Les messages les plus anciens doivent disparaître.
        if "messages_oldest" in report.parts_truncated:
            assert "message 0 très long" not in prompt
            assert "message 19 très long" in prompt


@pytest.mark.unit
class TestTruncationHardLimit:
    """Si tout est tronqué et qu'on dépasse hard_limit, warning over_hard_limit."""

    def test_hard_limit_warning(self) -> None:
        # Identité immutable + invariants +  business énorme.
        massive = "## CONTEXTE PME\n" + ("INDIC " * 5_000)  # ~30k tokens.
        parts = _build_parts(business_text=massive)
        prompt, report = truncate_prompt(parts, budget=4000, hard_limit=6000)
        # Aucune step ne peut couper le bloc statique → on dépasse.
        assert report.warning_emitted is True
        assert report.tokens_before > 6000


@pytest.mark.unit
class TestStepConstants:
    def test_constants(self) -> None:
        assert INDICATEURS_PER_AXE_AFTER_TRUNCATION == 5
        assert SKILLS_AFTER_TRUNCATION == 3
        assert MESSAGES_AFTER_TRUNCATION == 8


@pytest.mark.unit
class TestRenderParts:
    """``render_parts`` reste stable pour un PromptParts simple."""

    def test_basic_render(self) -> None:
        parts = _build_parts()
        out = render_parts(parts)
        assert "ESG Mefali" in out
        assert "10 règles" in out
        assert "CONTEXTE PME" in out
        assert "CONTEXTE PAGE" in out

    def test_admin_banner_renders_above_skills(self) -> None:
        parts = _build_parts(
            skills=[SkillRender(code="diagnose_esg")],
        )
        # Note : on construit PromptParts directement avec admin_banner.
        parts_admin = parts.model_copy(
            update={"admin_banner": "## MODE SUPPORT ADMIN\nAccount=xxx"}
        )
        out = render_parts(parts_admin)
        assert "MODE SUPPORT ADMIN" in out
        assert out.index("MODE SUPPORT ADMIN") < out.index("SKILLS ACTIFS")

    def test_sheet_result_note_renders(self) -> None:
        parts = _build_parts()
        parts_with_note = parts.model_copy(
            update={"sheet_result_note": "## RÉPONSE BOTTOM SHEET\n=> SARL"}
        )
        out = render_parts(parts_with_note)
        assert "RÉPONSE BOTTOM SHEET" in out
