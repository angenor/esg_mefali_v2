"""Tool ``ask_qcm`` — question à choix multiples (F15 US2).

Caller : ``app.orchestrator.tools.__init__.register_response_tools``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.orchestrator.tool_registry import tool
from app.orchestrator.tools._common import Option, no_html


class AskQcmPayload(BaseModel):
    """Payload pour ``ask_qcm`` : 2 à 20 options multi-sélectionnables."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=1024)
    options: list[Option] = Field(min_length=2, max_length=20)
    min_select: int | None = Field(default=None, ge=1)
    max_select: int | None = Field(default=None, ge=1)

    @field_validator("question")
    @classmethod
    def _no_html_question(cls, v: str) -> str:
        return no_html(v)

    @field_validator("options")
    @classmethod
    def _no_html_in_options(cls, v: list[Option]) -> list[Option]:
        for opt in v:
            no_html(opt.label)
            if opt.description is not None:
                no_html(opt.description)
        return v

    @model_validator(mode="after")
    def _check_bounds(self) -> AskQcmPayload:
        n = len(self.options)
        if self.min_select is not None and self.min_select > n:
            raise ValueError("min_select > nombre d'options")
        if self.max_select is not None and self.max_select > n:
            raise ValueError("max_select > nombre d'options")
        if (
            self.min_select is not None
            and self.max_select is not None
            and self.min_select > self.max_select
        ):
            raise ValueError("min_select > max_select")
        return self


def register() -> None:
    """Enregistre ``ask_qcm`` dans le tool_registry global."""
    tool(
        name="ask_qcm",
        description="Pose une question à choix multiples (cases à cocher).",
        use_when="L'utilisateur peut sélectionner plusieurs options (2..20).",
        dont_use_when="La sélection est exclusive (utiliser ask_qcu).",
        schema=AskQcmPayload,
        positive_examples=(
            {
                "question": "Quels piliers ESG vous concernent ?",
                "options": [
                    {"value": "E", "label": "Environnement"},
                    {"value": "S", "label": "Social"},
                    {"value": "G", "label": "Gouvernance"},
                ],
                "min_select": 1,
            },
        ),
    )


__all__ = ["AskQcmPayload", "register"]
