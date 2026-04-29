"""Package F15/F16 — tools de réponse + tools de visualisation inline.

Expose :
- ``register_response_tools()`` : tools de réponse F15 (bottom sheet).
- ``register_visualisation_tools()`` : tools de visualisation F16 (inline
  dans la bulle assistant).

Tools P2 F15 (``ask_date``, ``ask_date_range``, ``ask_rating``, ``show_form``)
sont DEFERRED dans le MVP F15.

Tools P2 F16 (``show_pie_chart``, ``show_donut_chart``, ``show_timeline``,
``show_comparison_table``, ``show_match_card``, ``show_progress_bar``,
``show_map``, ``show_mermaid``) et la réactivité historique (US13) sont
DEFERRED dans le MVP F16 — voir specs/016-tools-visualisation-inline/.
"""

from __future__ import annotations

from app.orchestrator.tools import (
    ask_file_upload,
    ask_number,
    ask_qcm,
    ask_qcu,
    ask_select,
    ask_yes_no,
    show_bar_chart,
    show_kpi_card,
    show_line_chart,
    show_radar_chart,
    show_summary_card,
)

_RESPONSE_REGISTRARS = (
    ask_qcu.register,
    ask_qcm.register,
    ask_yes_no.register,
    ask_select.register,
    ask_number.register,
    ask_file_upload.register,
    show_summary_card.register,
)

_VISUALISATION_REGISTRARS = (
    show_kpi_card.register,
    show_radar_chart.register,
    show_bar_chart.register,
    show_line_chart.register,
)


def register_response_tools() -> None:
    """Enregistre tous les tools de réponse F15 (P1 livrés)."""
    for register in _RESPONSE_REGISTRARS:
        register()


def register_visualisation_tools() -> None:
    """Enregistre tous les tools de visualisation F16 (P1 MVP livrés).

    P1 MVP : ``show_kpi_card``, ``show_radar_chart``, ``show_bar_chart``,
    ``show_line_chart``.
    """
    for register in _VISUALISATION_REGISTRARS:
        register()


__all__ = ["register_response_tools", "register_visualisation_tools"]
