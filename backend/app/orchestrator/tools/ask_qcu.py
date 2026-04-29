"""Tool ``ask_qcu`` — question à choix unique (F15 US1).

Caller : ``app.orchestrator.tools.__init__.register_response_tools``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.orchestrator.tool_registry import tool
from app.orchestrator.tools._common import Option, no_html


class AskQcuPayload(BaseModel):
    """Payload pour ``ask_qcu`` : 2 à 7 options exclusives."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=1024)
    options: list[Option] = Field(min_length=2, max_length=7)
    allow_other: bool = False

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


def register() -> None:
    """Enregistre ``ask_qcu`` dans le tool_registry global."""
    tool(
        name="ask_qcu",
        description="Pose une question à choix unique (radios).",
        use_when="L'utilisateur doit choisir UNE option parmi 2 à 7.",
        dont_use_when=(
            "La question est binaire (utiliser ask_yes_no) ou la liste est "
            "trop longue (utiliser ask_select)."
        ),
        schema=AskQcuPayload,
        positive_examples=(
            {
                "question": "Quelle est votre forme juridique ?",
                "options": [
                    {"value": "SARL", "label": "SARL"},
                    {"value": "SA", "label": "SA"},
                    {"value": "SAS", "label": "SAS"},
                ],
            },
        ),
    )


__all__ = ["AskQcuPayload", "register"]
