"""Tools fictifs MVP (US4) — base de tests et démo."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from app.orchestrator.tool_registry import tool


class ShowSummaryCardPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1)
    body: str = Field(min_length=1)


class AskQcuPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)
    choices: list[str] = Field(min_length=2, max_length=6)


class AskYesNoPayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1)


class UpdateDemoProfilePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    field: Literal["name", "sector", "size"]
    value: str = Field(min_length=1)


class SearchDemoSourcePayload(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str = Field(min_length=1)
    top_k: int = Field(default=5, ge=1, le=20)


def register_fixture_tools() -> None:
    """Enregistre les 5 tools fictifs dans le registre global."""
    tool(
        name="show_summary_card",
        description="Affiche une carte récapitulative en bottom sheet.",
        use_when="L'utilisateur demande un résumé d'une entité.",
        dont_use_when="L'utilisateur demande une mutation.",
        schema=ShowSummaryCardPayload,
        positive_examples=({"title": "Projet X", "body": "Résumé concis."},),
    )
    tool(
        name="ask_qcu",
        description="Pose une question à choix unique.",
        use_when="Plusieurs options possibles à clarifier.",
        dont_use_when="La question est binaire.",
        schema=AskQcuPayload,
    )
    tool(
        name="ask_yes_no",
        description="Pose une question oui/non.",
        use_when="Clarification binaire requise.",
        dont_use_when="Plus de deux options.",
        schema=AskYesNoPayload,
    )
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
