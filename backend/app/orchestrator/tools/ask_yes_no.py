"""Tool ``ask_yes_no`` — confirmation binaire (F15 US3).

Caller : ``app.orchestrator.tools.__init__.register_response_tools``.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.orchestrator.tool_registry import tool
from app.orchestrator.tools._common import no_html


class AskYesNoPayload(BaseModel):
    """Payload pour ``ask_yes_no`` : confirmation oui/non avec libellés custom."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=1024)
    yes_label: str = Field(default="Oui", min_length=1, max_length=64)
    no_label: str = Field(default="Non", min_length=1, max_length=64)

    @field_validator("question", "yes_label", "no_label")
    @classmethod
    def _no_html_text(cls, v: str) -> str:
        return no_html(v)


def register() -> None:
    """Enregistre ``ask_yes_no`` dans le tool_registry global."""
    tool(
        name="ask_yes_no",
        description="Pose une question oui/non (confirmation binaire).",
        use_when="Clarification binaire ou confirmation d'action destructive.",
        dont_use_when="Plus de deux options (utiliser ask_qcu/ask_qcm).",
        schema=AskYesNoPayload,
        positive_examples=(
            {
                "question": "Confirmer la suppression du projet ?",
                "yes_label": "Confirmer",
                "no_label": "Annuler",
            },
        ),
    )


__all__ = ["AskYesNoPayload", "register"]
