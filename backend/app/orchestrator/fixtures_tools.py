"""Tools fictifs MVP (US4) — base de tests et démo.

NOTE F15 : ``ask_qcu``, ``ask_yes_no`` et ``show_summary_card`` ont été
déplacés vers ``app.orchestrator.tools`` avec des schémas riches.
Seuls ``update_demo_profile`` et ``search_demo_source`` restent ici comme
fixtures pour les tests d'orchestration.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.orchestrator.tool_registry import tool


class UpdateDemoProfilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: Literal["name", "sector", "size"]
    value: str = Field(min_length=1)


class SearchDemoSourcePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


def register_fixture_tools() -> None:
    """Enregistre les tools de démonstration dans le registre global.

    Pour les tools de réponse F15 (``ask_qcu``, ``ask_yes_no``,
    ``show_summary_card``, etc.), utilisez
    ``app.orchestrator.tools.register_response_tools``.
    """
    tool(
        name="update_demo_profile",
        description="Met à jour un champ du profil de démonstration.",
        use_when="Mutation simple d'un champ scalaire.",
        dont_use_when="Mutation transactionnelle complexe.",
        schema=UpdateDemoProfilePayload,
    )
    tool(
        name="search_demo_source",
        description="Recherche dans les sources de démonstration.",
        use_when="L'utilisateur cite une source ou demande à vérifier.",
        dont_use_when="Aucun besoin de sourçage.",
        schema=SearchDemoSourcePayload,
    )


__all__ = ["register_fixture_tools"]
