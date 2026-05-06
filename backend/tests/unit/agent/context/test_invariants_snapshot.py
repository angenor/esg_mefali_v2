"""F54 / T019 — Snapshot test des invariants (SC-008).

Toute modification du contenu textuel des modules
:mod:`app.agent.prompts.identity` ou :mod:`app.agent.prompts.invariants` doit :

1. Régénérer le fichier ``snapshots/invariants_<version>.txt``.
2. Bumper :data:`PROMPT_VERSION` dans ``invariants.py`` après revue manuelle.

Ce test est volontairement fragile pour forcer la revue.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from app.agent.prompts.identity import IDENTITY_BLOCK
from app.agent.prompts.invariants import INVARIANTS_TEMPLATE, PROMPT_VERSION

_SNAPSHOT_DIR = Path(__file__).parent / "snapshots"


@pytest.mark.unit
def test_prompt_version_format() -> None:
    """``PROMPT_VERSION`` suit le format ``YYYY.MM`` (FR-015)."""
    assert isinstance(PROMPT_VERSION, str)
    assert len(PROMPT_VERSION) >= 6
    parts = PROMPT_VERSION.split(".")
    assert len(parts) == 2
    year, month = parts
    assert year.isdigit() and len(year) == 4
    assert month.isdigit() and 1 <= int(month) <= 12


@pytest.mark.unit
def test_snapshot_file_exists() -> None:
    """Un snapshot doit exister pour la PROMPT_VERSION courante."""
    snap_name = f"invariants_{PROMPT_VERSION.replace('.', '_')}.txt"
    snap_path = _SNAPSHOT_DIR / snap_name
    assert snap_path.exists(), (
        f"Snapshot manquant : {snap_path}. "
        f"Régénérer avec : python -c 'from app.agent.prompts.identity import IDENTITY_BLOCK; "
        f"from app.agent.prompts.invariants import INVARIANTS_TEMPLATE; "
        f"open(\"{snap_path}\", \"w\").write(IDENTITY_BLOCK + chr(10) + INVARIANTS_TEMPLATE)'"
    )


@pytest.mark.unit
def test_snapshot_matches_current_template() -> None:
    """Le contenu actuel doit matcher le snapshot (SC-008)."""
    snap_name = f"invariants_{PROMPT_VERSION.replace('.', '_')}.txt"
    snap_path = _SNAPSHOT_DIR / snap_name
    expected = snap_path.read_text(encoding="utf-8")
    actual = IDENTITY_BLOCK + "\n" + INVARIANTS_TEMPLATE
    assert actual == expected, (
        "INVARIANTS_TEMPLATE / IDENTITY_BLOCK ont changé sans bump de "
        "PROMPT_VERSION. Soit (a) revertir le diff, soit (b) bumper "
        "PROMPT_VERSION et régénérer le snapshot."
    )


@pytest.mark.unit
def test_identity_block_mentions_esg_mefali() -> None:
    """Le bloc d'identité doit explicitement nommer ESG Mefali (SC-009)."""
    assert "ESG Mefali" in IDENTITY_BLOCK


@pytest.mark.unit
def test_identity_block_forbids_naming_underlying_model() -> None:
    """Le bloc d'identité doit interdire la révélation du modèle (SC-009)."""
    lower = IDENTITY_BLOCK.lower()
    # Liste des termes que le prompt doit citer pour interdire leur usage.
    forbidden_to_reveal = ["minimax", "gpt", "claude", "anthropic", "openai"]
    # On vérifie que le prompt mentionne au moins quelques-uns de ces noms
    # comme exemples interdits.
    cited = sum(1 for k in forbidden_to_reveal if k in lower)
    assert cited >= 3, (
        "Le bloc d'identité doit citer plusieurs noms de modèles interdits "
        f"pour les nommer comme tabous. Trouvés : {cited}/5"
    )


@pytest.mark.unit
def test_invariants_template_lists_all_10_principles() -> None:
    """Les 10 principes P1..P10 doivent tous figurer dans le template."""
    for i in range(1, 11):
        marker = f"## P{i} —"
        assert marker in INVARIANTS_TEMPLATE, (
            f"Le principe {marker} est manquant dans INVARIANTS_TEMPLATE."
        )


@pytest.mark.unit
def test_invariants_no_hardcoded_skill_or_tool_name() -> None:
    """SC-013 : aucun nom de tool ou skill spécifique en dur dans le template
    d'invariants — seulement des principes généraux.
    """
    # Tools/skills connus du registry F14/F19 qu'on ne veut PAS voir nommés.
    forbidden = [
        "update_company_profile",
        "create_project",
        "generate_attestation",
        "diagnose_esg",
        "compute_carbon",
        "show_score_evolution",
        "ask_qcu",
        "ask_form",
        "show_chart",
        "cite_source",
    ]
    for name in forbidden:
        assert name not in INVARIANTS_TEMPLATE, (
            f"Le tool/skill {name!r} est nommé en dur dans INVARIANTS_TEMPLATE — "
            f"viole SC-013. Reformule en termes de principe."
        )
