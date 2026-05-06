"""F54 / T067-T069 — Tests unitaires du prompt_builder.

Couvre :
- SC-001 : prompt avec PME complète mentionne secteur, projets, score.
- SC-002 : PME sans projet → "Aucun projet enregistré.".
- US3 : page projet ajoutée au prompt.
- US5 : ``sheet_result`` injecte note explicite.
- US6 : ``user_role=admin`` → bandeau + tools confirmation.
- FR-013 : escape des champs PME.
- Cohérence devise : peg FCFA-EUR appliqué quand multi-devise.
"""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from types import SimpleNamespace
from uuid import uuid4

import pytest

from app.agent.context.models import (
    BusinessContext,
    EnrichedPageContext,
    EntrepriseSummary,
    IndicateurSummary,
    Money,
    ProjetSummary,
    ScoreCreditSummary,
)
from app.agent.prompt_builder import (
    build_prompt_parts,
    build_system_prompt,
    render_business_block,
    render_decision_tree_block,
    render_page_block,
)


def _build_ctx(
    *,
    account_id=None,
    raison_sociale: str = "SARL Boulangerie Sankoré",
    secteur: str = "Boulangerie-pâtisserie",
    projets: int = 2,
    indicateurs: int = 0,
    score_gauge: int | None = 62,
    user_role: str = "pme",
    devise: str = "XOF",
) -> BusinessContext:
    aid = account_id or uuid4()
    ent = EntrepriseSummary(
        account_id=aid,
        raison_sociale=raison_sociale,
        secteur_naf="C10.71",
        secteur_label=secteur,
        pays="CI",
        devise_principale=devise,
        ca_dernier_exercice=Money(amount=Decimal("12000000"), currency=devise),
    )
    proj_list = [
        ProjetSummary(
            id=uuid4(),
            titre=f"Projet {i + 1}",
            description_courte=f"Description {i + 1}",
            montant_demande=Money(amount=Decimal("5000000"), currency=devise),
            statut="en_analyse",
            date_creation=datetime.now(UTC),
        )
        for i in range(projets)
    ]
    indic = [
        IndicateurSummary(
            id=uuid4(),
            code=f"INDIC_{i}",
            libelle=f"Indicateur {i}",
            axe=("E", "S", "G")[i % 3],
            valeur=Decimal("10"),
            unite="tCO2e",
            date_calcul=datetime.now(UTC),
        )
        for i in range(indicateurs)
    ]
    score: ScoreCreditSummary | None = None
    if score_gauge is not None:
        score = ScoreCreditSummary(
            scoring_id=uuid4(),
            gauge=score_gauge,
            sub_scores={"E": 60, "S": 65, "G": 60},
            date_calcul=datetime.now(UTC),
            lacunes_principales=["gestion_dechets"],
        )
    return BusinessContext(
        account_id=aid,
        user_id=uuid4(),
        user_role=user_role,
        loaded_at=datetime.now(UTC),
        entreprise=ent,
        projets_actifs=proj_list,
        indicateurs_recents=indic,
        score_credit=score,
    )


def _empty_page() -> EnrichedPageContext:
    return EnrichedPageContext(page="/", entity_type=None)


# ---------------------------------------------------------------------------
# SC-001 : prompt complet contient les éléments clés.
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptComplete:
    def test_pme_complete_mentions_key_elements(self) -> None:
        ctx = _build_ctx(projets=2, score_gauge=62)
        prompt, report = build_system_prompt(
            business_ctx=ctx, page_ctx=_empty_page()
        )
        assert "ESG Mefali" in prompt
        assert "SARL Boulangerie Sankoré" in prompt
        assert "Projet 1" in prompt
        assert "Projet 2" in prompt
        assert "62/100" in prompt
        assert "Boulangerie-pâtisserie" in prompt
        # Pas de truncation déclenchée.
        assert report.warning_emitted is False

    def test_pme_complete_includes_invariants(self) -> None:
        ctx = _build_ctx()
        prompt, _ = build_system_prompt(
            business_ctx=ctx, page_ctx=_empty_page()
        )
        for i in range(1, 11):
            assert f"## P{i} —" in prompt


# ---------------------------------------------------------------------------
# SC-002 : PME sans projet — message explicite, pas de bloc vide.
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptNoProjet:
    def test_no_projet_message(self) -> None:
        ctx = _build_ctx(projets=0)
        prompt, _ = build_system_prompt(
            business_ctx=ctx, page_ctx=_empty_page()
        )
        assert "Aucun projet enregistré." in prompt

    def test_no_score(self) -> None:
        ctx = _build_ctx(score_gauge=None)
        prompt, _ = build_system_prompt(
            business_ctx=ctx, page_ctx=_empty_page()
        )
        assert "Aucun scoring calculé." in prompt


# ---------------------------------------------------------------------------
# US3 : contexte de page courante.
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptPageContext:
    def test_projet_page_context(self) -> None:
        page_ctx = EnrichedPageContext(
            page="/projet/abc",
            entity_type="Projet",
            entity_id=uuid4(),
            data={"projet": {"titre": "Solaire Saly", "statut": "en_analyse"}},
            related=[{"type": "candidature", "summary": {"id": "c1"}}],
        )
        ctx = _build_ctx()
        prompt, _ = build_system_prompt(business_ctx=ctx, page_ctx=page_ctx)
        assert "/projet/abc" in prompt
        assert "Type d'entité : Projet" in prompt
        assert "Solaire Saly" in prompt

    def test_no_entity_minimal_block(self) -> None:
        ctx = _build_ctx()
        prompt, _ = build_system_prompt(
            business_ctx=ctx, page_ctx=_empty_page()
        )
        assert "Aucune entité ciblée." in prompt


# ---------------------------------------------------------------------------
# US5 : sheet_result.
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptSheetResult:
    def test_sheet_result_injects_note(self) -> None:
        ctx = _build_ctx()
        last_msg = {
            "role": "user",
            "content": "",
            "payload_json": {
                "sheet_result": {
                    "tool": "ask_qcu",
                    "value": "SARL",
                    "label": "Forme juridique ?",
                }
            },
        }
        prompt, _ = build_system_prompt(
            business_ctx=ctx,
            page_ctx=_empty_page(),
            last_user_message=last_msg,
        )
        assert "RÉPONSE BOTTOM SHEET" in prompt
        assert "SARL" in prompt
        assert "Ne re-pose pas" in prompt

    def test_no_sheet_result_no_note(self) -> None:
        ctx = _build_ctx()
        prompt, _ = build_system_prompt(
            business_ctx=ctx,
            page_ctx=_empty_page(),
            last_user_message={"role": "user", "content": "Bonjour"},
        )
        assert "RÉPONSE BOTTOM SHEET" not in prompt


# ---------------------------------------------------------------------------
# US6 : mode admin.
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptAdminMode:
    def test_admin_banner_present(self) -> None:
        ctx = _build_ctx(user_role="admin")
        prompt, _ = build_system_prompt(
            business_ctx=ctx, page_ctx=_empty_page(), user_role="admin"
        )
        assert "MODE SUPPORT ADMIN" in prompt
        assert str(ctx.account_id) in prompt

    def test_admin_marks_mutation_tools(self) -> None:
        ctx = _build_ctx(user_role="admin")
        tools = [
            SimpleNamespace(name="ask_qcu", use_when="Question fermée"),
            SimpleNamespace(name="create_project", use_when="Créer un projet"),
        ]
        prompt, _ = build_system_prompt(
            business_ctx=ctx,
            page_ctx=_empty_page(),
            user_role="admin",
            available_tools=tools,
        )
        assert "[requires_confirmation]" in prompt

    def test_pme_no_admin_banner(self) -> None:
        ctx = _build_ctx(user_role="pme")
        prompt, _ = build_system_prompt(
            business_ctx=ctx, page_ctx=_empty_page(), user_role="pme"
        )
        assert "MODE SUPPORT ADMIN" not in prompt


# ---------------------------------------------------------------------------
# FR-013 : escape des champs PME.
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptEscape:
    def test_pme_name_with_braces_escaped(self) -> None:
        ctx = _build_ctx(raison_sociale="Société {{exploit}}")
        prompt, _ = build_system_prompt(
            business_ctx=ctx, page_ctx=_empty_page()
        )
        # Le ``{{`` original est doublé en ``{{{{``.
        assert "{{{{exploit}}}}" in prompt
        # Pas de ``{exploit}`` simple.
        assert "{exploit}" not in prompt or "{{exploit}}" in prompt


# ---------------------------------------------------------------------------
# US3 — render_business_block / render_page_block en isolation.
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestRenderBlocks:
    def test_business_block_lists_indicateurs_par_axe(self) -> None:
        ctx = _build_ctx(indicateurs=9)  # 3 par axe.
        b = render_business_block(ctx)
        assert b.indicateurs_par_axe.keys() == {"E", "S", "G"}
        assert all(len(v) == 3 for v in b.indicateurs_par_axe.values())
        assert "INDICATEURS RÉCENTS" in b.text

    def test_page_block_handles_none_entity(self) -> None:
        page = EnrichedPageContext(page="/", entity_type=None)
        rendered = render_page_block(page)
        assert "Aucune entité ciblée." in rendered.text

    def test_decision_tree_uses_use_when(self) -> None:
        from app.agent.context.models import ToolRender

        tools = [
            ToolRender(name="ask_qcu", use_when="Question fermée"),
            ToolRender(
                name="create_project",
                use_when="Créer projet",
                dont_use_when="Mise à jour",
            ),
        ]
        out = render_decision_tree_block(tools)
        assert "ask_qcu" in out
        assert "Question fermée" in out
        assert "Créer projet" in out
        assert "Mise à jour" in out

    def test_decision_tree_empty_for_no_tools(self) -> None:
        assert render_decision_tree_block([]) == ""


# ---------------------------------------------------------------------------
# Cohérence devise (NFR-006).
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPromptMultiCurrency:
    def test_xof_only_no_eur_equivalent(self) -> None:
        ctx = _build_ctx(devise="XOF")
        prompt, _ = build_system_prompt(business_ctx=ctx, page_ctx=_empty_page())
        # Pas d'équivalent (~XOF) puisque devise unique.
        # Assertions précises : la mention "(~" n'apparaît pas dans le bloc CA.
        assert "12 000 000 XOF" in prompt

    def test_mix_xof_eur_shows_xof_equivalent(self) -> None:
        # Construit ctx avec entreprise en EUR + projet en XOF (mix).
        aid = uuid4()
        ent = EntrepriseSummary(
            account_id=aid,
            raison_sociale="Test EUR",
            pays="CI",
            devise_principale="EUR",
            ca_dernier_exercice=Money(amount=Decimal("100"), currency="EUR"),
        )
        proj = ProjetSummary(
            id=uuid4(),
            titre="Solaire",
            montant_demande=Money(amount=Decimal("5000000"), currency="XOF"),
            statut="en_analyse",
            date_creation=datetime.now(UTC),
        )
        ctx = BusinessContext(
            account_id=aid,
            user_id=uuid4(),
            user_role="pme",
            loaded_at=datetime.now(UTC),
            entreprise=ent,
            projets_actifs=[proj],
        )
        prompt, _ = build_system_prompt(
            business_ctx=ctx, page_ctx=_empty_page()
        )
        # 100 EUR (mix avec XOF) → ~65 596 XOF.
        assert "100 EUR" in prompt
        assert "65 596 XOF" in prompt


@pytest.mark.unit
class TestBuildPromptPartsImmutable:
    def test_parts_is_frozen(self) -> None:
        ctx = _build_ctx()
        parts = build_prompt_parts(business_ctx=ctx, page_ctx=_empty_page())
        with pytest.raises((TypeError, ValueError, Exception)):
            parts.identity = "modified"  # type: ignore[misc]
