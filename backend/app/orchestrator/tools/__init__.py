"""Package F15 — tools de réponse en bottom sheet.

Expose ``register_response_tools()`` qui enregistre tous les tools P1 livrés
dans le ``TOOL_REGISTRY`` global (F14).

Tools P2 (``ask_date``, ``ask_date_range``, ``ask_rating``, ``show_form``)
sont DEFERRED dans le MVP F15.
"""

from __future__ import annotations

from app.orchestrator.tools import (
    ask_file_upload,
    ask_number,
    ask_qcm,
    ask_qcu,
    ask_select,
    ask_yes_no,
    show_summary_card,
)

_REGISTRARS = (
    ask_qcu.register,
    ask_qcm.register,
    ask_yes_no.register,
    ask_select.register,
    ask_number.register,
    ask_file_upload.register,
    show_summary_card.register,
)


def register_response_tools() -> None:
    """Enregistre tous les tools de réponse F15 (P1 livrés)."""
    for register in _REGISTRARS:
        register()


__all__ = ["register_response_tools"]
