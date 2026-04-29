"""Tool ``ask_file_upload`` — upload contextualisé (F15 US8).

Caller : ``app.orchestrator.tools.__init__.register_response_tools``.
"""

from __future__ import annotations

from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.orchestrator.tool_registry import tool
from app.orchestrator.tools._common import no_html


class AttachTo(BaseModel):
    """Cible de rattachement de l'upload (projet ou entreprise)."""

    model_config = ConfigDict(extra="forbid")

    entity_type: Literal["projet", "entreprise"]
    entity_id: UUID | None = None


class AskFileUploadPayload(BaseModel):
    """Payload pour ``ask_file_upload`` : bouton d'upload contextualisé."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=1024)
    attach_to: AttachTo
    accepted_mime: list[str] = Field(min_length=1, max_length=10)
    max_size_mb: int = Field(ge=1, le=100)

    @field_validator("question")
    @classmethod
    def _no_html_question(cls, v: str) -> str:
        return no_html(v)

    @field_validator("accepted_mime")
    @classmethod
    def _check_mime(cls, v: list[str]) -> list[str]:
        for m in v:
            no_html(m)
            if "/" not in m:
                raise ValueError(f"MIME invalide : {m!r}")
        return v


def register() -> None:
    """Enregistre ``ask_file_upload`` dans le tool_registry global."""
    tool(
        name="ask_file_upload",
        description="Demande à l'utilisateur d'uploader un document.",
        use_when=(
            "Le LLM doit récupérer un document (business plan, bilan, "
            "factures) via F12/F22."
        ),
        dont_use_when="L'information est saisie directement (utiliser ask_qcu/number).",
        schema=AskFileUploadPayload,
        positive_examples=(
            {
                "question": "Pouvez-vous uploader votre business plan ?",
                "attach_to": {"entity_type": "projet"},
                "accepted_mime": ["application/pdf"],
                "max_size_mb": 10,
            },
        ),
    )


__all__ = ["AskFileUploadPayload", "AttachTo", "register"]
