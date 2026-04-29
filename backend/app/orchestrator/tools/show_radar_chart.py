"""Tool ``show_radar_chart`` — radar multi-axes (F16 US3).

Caller : ``app.orchestrator.tools.__init__.register_visualisation_tools``.
"""

from __future__ import annotations

from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from app.orchestrator.tool_registry import tool
from app.orchestrator.tools._common import no_html
from app.orchestrator.tools._viz_common import AltTextMixin, SourceRequiredMixin


class RadarSeries(BaseModel):
    """Une série de valeurs alignées sur ``axes``."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1, max_length=64)
    values: list[Decimal] = Field(min_length=1)

    @field_validator("name")
    @classmethod
    def _no_html(cls, v: str) -> str:
        return no_html(v)


class ShowRadarChartPayload(SourceRequiredMixin, AltTextMixin):
    """Payload ``show_radar_chart`` : axes, séries, sources."""

    model_config = ConfigDict(extra="forbid")

    title: str = Field(min_length=1, max_length=256)
    axes: list[str] = Field(min_length=3, max_length=12)
    series: list[RadarSeries] = Field(min_length=1, max_length=5)

    @field_validator("title")
    @classmethod
    def _no_html_title(cls, v: str) -> str:
        return no_html(v)

    @field_validator("axes")
    @classmethod
    def _validate_axes(cls, v: list[str]) -> list[str]:
        for axis in v:
            if not axis or len(axis) > 64:
                raise ValueError("each axis label must be 1..64 chars")
            no_html(axis)
        return v

    @model_validator(mode="after")
    def _check_series_lengths(self) -> ShowRadarChartPayload:
        n = len(self.axes)
        for s in self.series:
            if len(s.values) != n:
                raise ValueError(
                    f"series '{s.name}' has {len(s.values)} values, expected {n}"
                )
        return self


def register() -> None:
    """Enregistre ``show_radar_chart`` dans le tool_registry global."""
    tool(
        name="show_radar_chart",
        description="Radar multi-axes pour visualiser un profil sur plusieurs "
        "dimensions (E/S/G ou multi-référentiels).",
        use_when=(
            "Comparer plusieurs piliers ou plusieurs référentiels d'un seul "
            "coup d'œil."
        ),
        dont_use_when="Une seule dimension — utiliser show_kpi_card ou show_bar_chart.",
        schema=ShowRadarChartPayload,
        positive_examples=(
            {
                "title": "Score ESG par pilier (Mefali vs GCF)",
                "axes": [
                    "Environnement",
                    "Social",
                    "Gouvernance",
                    "Climat",
                    "Diversité",
                ],
                "series": [
                    {"name": "Mefali", "values": ["72", "65", "80", "60", "75"]},
                    {"name": "GCF", "values": ["75", "70", "78", "70", "72"]},
                ],
                "source_ids": [21, 22],
                "alt_text": "Radar comparant Mefali et GCF sur 5 piliers.",
            },
        ),
    )


__all__ = ["RadarSeries", "ShowRadarChartPayload", "register"]
