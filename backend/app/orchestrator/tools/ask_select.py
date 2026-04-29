"""Tool ``ask_select`` — sélection dans liste longue avec recherche (F15 US4).

Caller : ``app.orchestrator.tools.__init__.register_response_tools``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.orchestrator.tool_registry import tool
from app.orchestrator.tools._common import Option, no_html


class AskSelectPayload(BaseModel):
    """Payload pour ``ask_select`` : options inline OU endpoint paginé."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=1024)
    options: list[Option] | None = None
    options_endpoint: str | None = Field(default=None, pattern=r"^/")
    multi: bool = False

    @field_validator("question")
    @classmethod
    def _no_html_question(cls, v: str) -> str:
        return no_html(v)

    @field_validator("options")
    @classmethod
    def _no_html_in_options(cls, v: list[Option] | None) -> list[Option] | None:
        if v is None:
            return v
        for opt in v:
            no_html(opt.label)
            if opt.description is not None:
                no_html(opt.description)
        return v

    @model_validator(mode="after")
    def _xor_options(self) -> AskSelectPayload:
        has_inline = self.options is not None
        has_endpoint = self.options_endpoint is not None
        if has_inline == has_endpoint:
            raise ValueError(
                "Fournir exactement un de 'options' ou 'options_endpoint'."
            )
        return self


def register() -> None:
    """Enregistre ``ask_select`` dans le tool_registry global."""
    tool(
        name="ask_select",
        description="Sélection dans une liste longue avec recherche.",
        use_when=(
            "Plus de 7 options ou liste dynamique (pays, secteur, fonds, "
            "intermédiaire, source)."
        ),
        dont_use_when="Liste courte et statique (utiliser ask_qcu).",
        schema=AskSelectPayload,
        positive_examples=(
            {
                "question": "Quel est votre secteur d'activité ?",
                "options_endpoint": "/me/catalog/secteurs",
            },
        ),
    )


__all__ = ["AskSelectPayload", "register"]
