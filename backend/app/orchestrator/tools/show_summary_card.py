"""Tool ``show_summary_card`` — carte récap actionnable (F15 US10).

Caller : ``app.orchestrator.tools.__init__.register_response_tools``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.orchestrator.tool_registry import tool
from app.orchestrator.tools._common import no_html


class SummaryField(BaseModel):
    """Une ligne label/value/source dans la carte récap."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=128)
    value: str = Field(max_length=2048)
    source: str | None = Field(default=None, max_length=256)


class SummaryAction(BaseModel):
    """Une action proposée à l'utilisateur sur la carte récap."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=64)
    kind: Literal["confirm", "edit", "cancel"]


class ShowSummaryCardPayload(BaseModel):
    """Payload pour ``show_summary_card`` : titre + champs + actions."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=256)
    fields: list[SummaryField] = Field(min_length=1, max_length=30)
    actions: list[SummaryAction] = Field(min_length=1, max_length=5)

    @field_validator("title")
    @classmethod
    def _no_html_title(cls, v: str) -> str:
        return no_html(v)

    @field_validator("fields")
    @classmethod
    def _no_html_in_fields(cls, v: list[SummaryField]) -> list[SummaryField]:
        for f in v:
            no_html(f.label)
            no_html(f.value)
            if f.source is not None:
                no_html(f.source)
        return v

    @field_validator("actions")
    @classmethod
    def _no_html_in_actions(cls, v: list[SummaryAction]) -> list[SummaryAction]:
        for a in v:
            no_html(a.label)
        return v


def register() -> None:
    """Enregistre ``show_summary_card`` dans le tool_registry global."""
    tool(
        name="show_summary_card",
        description="Affiche une carte récap avec actions (confirm/edit/cancel).",
        use_when=(
            "Le LLM a extrait/calculé des informations à valider par "
            "l'utilisateur (OCR, pré-remplissage)."
        ),
        dont_use_when="Pas de validation requise (utiliser un message texte simple).",
        schema=ShowSummaryCardPayload,
        positive_examples=(
            {
                "title": "Voici ce que j'ai compris",
                "fields": [
                    {"label": "Nom", "value": "ACME SARL"},
                    {"label": "Effectifs", "value": "12"},
                ],
                "actions": [
                    {"label": "Valider", "kind": "confirm"},
                    {"label": "Corriger", "kind": "edit"},
                    {"label": "Annuler", "kind": "cancel"},
                ],
            },
        ),
    )


__all__ = [
    "ShowSummaryCardPayload",
    "SummaryAction",
    "SummaryField",
    "register",
]
