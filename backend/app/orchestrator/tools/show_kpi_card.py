"""Tool ``show_kpi_card`` — chiffre clé + delta (F16 US1).

Caller : ``app.orchestrator.tools.__init__.register_visualisation_tools``.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.orchestrator.tool_registry import tool
from app.orchestrator.tools._common import no_html
from app.orchestrator.tools._viz_common import AltTextMixin, SourceRequiredMixin


class KpiDelta(BaseModel):
    """Variation associée au KPI (ex : ``-12 vs 2024``)."""

    model_config = ConfigDict(extra="forbid")

    value: Decimal
    period: str = Field(min_length=1, max_length=32)

    @field_validator("period")
    @classmethod
    def _no_html(cls, v: str) -> str:
        return no_html(v)


class ShowKpiCardPayload(SourceRequiredMixin, AltTextMixin):
    """Payload ``show_kpi_card`` : valeur, unité, delta, source(s)."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=128)
    value: Decimal
    unit: str = Field(min_length=1, max_length=32)
    delta: KpiDelta | None = None

    @field_validator("label", "unit")
    @classmethod
    def _no_html(cls, v: str) -> str:
        return no_html(v)


def register() -> None:
    """Enregistre ``show_kpi_card`` dans le tool_registry global."""
    tool(
        name="show_kpi_card",
        description="Affiche un chiffre clé mis en valeur avec son contexte, "
        "un delta éventuel et une source cliquable.",
        use_when=(
            "Un chiffre unique mérite d'être mis en exergue (score ESG global, "
            "empreinte carbone annuelle, montant levé)."
        ),
        dont_use_when=(
            "Plusieurs valeurs liées à comparer — utiliser show_bar_chart "
            "ou show_radar_chart."
        ),
        schema=ShowKpiCardPayload,
        positive_examples=(
            {
                "label": "Empreinte carbone 2025",
                "value": "45.00",
                "unit": "tCO2e",
                "delta": {"value": "-12.0", "period": "vs 2024"},
                "source_ids": [42],
                "alt_text": "Empreinte carbone 2025 : 45 tCO2e, -12% vs 2024.",
            },
        ),
    )


__all__ = ["KpiDelta", "ShowKpiCardPayload", "register"]
