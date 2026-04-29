"""Tool ``show_bar_chart`` — barres pour ventilation/benchmarking (F16 US4).

Caller : ``app.orchestrator.tools.__init__.register_visualisation_tools``.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.orchestrator.tool_registry import tool
from app.orchestrator.tools._common import no_html
from app.orchestrator.tools._viz_common import AltTextMixin, SourceRequiredMixin


class Bar(BaseModel):
    """Une barre du graphique (étiquette + valeur)."""

    model_config = ConfigDict(extra="forbid")

    label: str = Field(min_length=1, max_length=64)
    value: Decimal

    @field_validator("label")
    @classmethod
    def _no_html(cls, v: str) -> str:
        return no_html(v)


class ShowBarChartPayload(SourceRequiredMixin, AltTextMixin):
    """Payload ``show_bar_chart`` : barres comparées."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=256)
    x_label: str = Field(default="", max_length=64)
    y_label: str = Field(default="", max_length=64)
    bars: list[Bar] = Field(min_length=1, max_length=20)

    @field_validator("title", "x_label", "y_label")
    @classmethod
    def _no_html(cls, v: str) -> str:
        return no_html(v)


def register() -> None:
    """Enregistre ``show_bar_chart`` dans le tool_registry global."""
    tool(
        name="show_bar_chart",
        description="Diagramme en barres pour ventilation ou benchmarking.",
        use_when="Comparer plusieurs catégories sur une même métrique.",
        dont_use_when=(
            "Évolution temporelle — utiliser show_line_chart ; "
            "répartition d'un total — utiliser show_pie_chart."
        ),
        schema=ShowBarChartPayload,
        positive_examples=(
            {
                "title": "Score ESG par référentiel",
                "x_label": "Référentiel",
                "y_label": "Score /100",
                "bars": [
                    {"label": "Mefali", "value": "72"},
                    {"label": "GCF", "value": "68"},
                    {"label": "IFC", "value": "70"},
                    {"label": "BOAD", "value": "65"},
                ],
                "source_ids": [21, 22, 23, 24],
                "alt_text": "Score ESG par référentiel.",
            },
        ),
    )


__all__ = ["Bar", "ShowBarChartPayload", "register"]
