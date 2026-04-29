"""Tool ``ask_number`` — saisie numérique typée (F15 US5).

Caller : ``app.orchestrator.tools.__init__.register_response_tools``.
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.orchestrator.tool_registry import tool
from app.orchestrator.tools._common import no_html


class MoneySpec(BaseModel):
    """Spécification monétaire pour les montants typés."""

    model_config = ConfigDict(extra="forbid")

    currency: Literal["XOF", "EUR"]


class AskNumberPayload(BaseModel):
    """Payload pour ``ask_number`` : nombre avec unité, bornes, money optionnelle."""

    model_config = ConfigDict(extra="forbid")

    question: str = Field(min_length=1, max_length=1024)
    unit: str = Field(min_length=1, max_length=32)
    min: float | None = None
    max: float | None = None
    step: float | None = Field(default=None, gt=0)
    money: MoneySpec | None = None

    @field_validator("question", "unit")
    @classmethod
    def _no_html_text(cls, v: str) -> str:
        return no_html(v)

    @model_validator(mode="after")
    def _check_bounds(self) -> AskNumberPayload:
        if self.min is not None and self.max is not None and self.min > self.max:
            raise ValueError("min > max")
        return self


def register() -> None:
    """Enregistre ``ask_number`` dans le tool_registry global."""
    tool(
        name="ask_number",
        description="Saisie d'un nombre avec unité, bornes et conversion money optionnelle.",
        use_when="Saisie chiffrée (CA, effectifs, montant, tCO2e).",
        dont_use_when="La valeur est qualitative (utiliser ask_qcu/ask_select).",
        schema=AskNumberPayload,
        positive_examples=(
            {
                "question": "Quel est votre chiffre d'affaires annuel ?",
                "unit": "XOF",
                "min": 0,
                "money": {"currency": "XOF"},
            },
        ),
    )


__all__ = ["AskNumberPayload", "MoneySpec", "register"]
