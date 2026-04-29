"""Schémas Pydantic du pipeline F14 — orchestration LangGraph.

Tous les modèles utilisent ``extra='forbid'`` pour une validation stricte
(invariant US4 / US6 du spec).
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field

ToolCallStatus = Literal["ok", "validation_error", "fallback", "handler_error"]

Intent = Literal[
    "profilage",
    "mutation",
    "analyse",
    "navigation",
    "question_fermee",
    "aide",
    "autre",
]


class ValidationErrorDetail(BaseModel):
    """Erreur structurée renvoyée au LLM pour retry (US6)."""

    model_config = ConfigDict(extra="forbid")

    field: str
    received: Any | None = None
    expected: str
    message: str


class ToolCallResult(BaseModel):
    """Résultat d'une tentative d'exécution de tool dans le pipeline."""

    model_config = ConfigDict(extra="forbid")

    tool_name: str
    status: ToolCallStatus
    payload: dict[str, Any] | None = None
    errors: list[ValidationErrorDetail] = Field(default_factory=list)
    retries: int = 0


class PipelineResponse(BaseModel):
    """Réponse finale du pipeline (US1)."""

    model_config = ConfigDict(extra="forbid")

    intent: Intent
    selected_tools: list[str]
    tool_call: ToolCallResult | None = None
    fallback_text: str | None = None
