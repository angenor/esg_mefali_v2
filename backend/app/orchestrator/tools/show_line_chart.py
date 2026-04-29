"""Tool ``show_line_chart`` — courbe d'évolution dans le temps (F16 US5).

Caller : ``app.orchestrator.tools.__init__.register_visualisation_tools``.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.orchestrator.tool_registry import tool
from app.orchestrator.tools._common import no_html
from app.orchestrator.tools._viz_common import AltTextMixin, SourceRequiredMixin


class LinePoint(BaseModel):
    """Un point d'une série (x catégoriel ou numérique, y numérique)."""

    model_config = ConfigDict(extra="forbid")

    x: str | Decimal
    y: Decimal

    @field_validator("x")
    @classmethod
    def _no_html_x(cls, v: str | Decimal) -> str | Decimal:
        if isinstance(v, str):
            if not v or len(v) > 32:
                raise ValueError("x string must be 1..32 chars")
            no_html(v)
        return v


class LineSeries(BaseModel):
    """Une série de points pour ``show_line_chart``."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=64)
    points: list[LinePoint] = Field(min_length=1, max_length=50)

    @field_validator("name")
    @classmethod
    def _no_html_name(cls, v: str) -> str:
        return no_html(v)


class ShowLineChartPayload(SourceRequiredMixin, AltTextMixin):
    """Payload ``show_line_chart`` : courbe(s) d'évolution."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=256)
    x_label: str = Field(default="", max_length=64)
    y_label: str = Field(default="", max_length=64)
    series: list[LineSeries] = Field(min_length=1, max_length=5)

    @field_validator("title", "x_label", "y_label")
    @classmethod
    def _no_html(cls, v: str) -> str:
        return no_html(v)


def register() -> None:
    """Enregistre ``show_line_chart`` dans le tool_registry global."""
    tool(
        name="show_line_chart",
        description="Courbe d'évolution dans le temps.",
        use_when="Tendance mensuelle/annuelle d'une métrique.",
        dont_use_when="Pas d'axe temps — utiliser un autre tool.",
        schema=ShowLineChartPayload,
        positive_examples=(
            {
                "title": "Évolution empreinte carbone (12 mois)",
                "x_label": "Mois",
                "y_label": "tCO2e",
                "series": [
                    {
                        "name": "2025",
                        "points": [
                            {"x": "2025-01", "y": "5.2"},
                            {"x": "2025-02", "y": "4.9"},
                        ],
                    }
                ],
                "source_ids": [42],
                "alt_text": "Empreinte mensuelle 2025.",
            },
        ),
    )


__all__ = ["LinePoint", "LineSeries", "ShowLineChartPayload", "register"]
