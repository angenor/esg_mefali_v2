"""F58 / US6 — Tests du tagging automatique de ``flow`` (sous-quotas).

Vérifie que :
- ``infer_flow`` détecte ``ocr_analysis`` quand le route/skill/node mentionne
  un mot-clé OCR/document.
- ``infer_flow`` retourne ``conversation`` par défaut.
- ``record_step`` rejette les flows invalides.
- ``record_step`` écrit le flow correct (vérifié indirectement via
  agrégation budget).
"""

from __future__ import annotations

import pytest

from app.agent.repository import infer_flow


@pytest.mark.unit
def test_infer_flow_default_is_conversation() -> None:
    assert infer_flow() == "conversation"


@pytest.mark.unit
def test_infer_flow_ocr_route_returns_ocr_analysis() -> None:
    assert infer_flow(page_route="/projets/123/ocr") == "ocr_analysis"
    assert infer_flow(page_route="/documents/upload") == "ocr_analysis"
    assert infer_flow(page_route="/projets/abc/scan") == "ocr_analysis"


@pytest.mark.unit
def test_infer_flow_chat_route_returns_conversation() -> None:
    assert infer_flow(page_route="/chat") == "conversation"
    assert infer_flow(page_route="/dashboard") == "conversation"
    assert infer_flow(page_route="/projets/123") == "conversation"


@pytest.mark.unit
def test_infer_flow_ocr_skill_returns_ocr_analysis() -> None:
    assert infer_flow(skill_name="ocr_extract_invoice") == "ocr_analysis"
    assert infer_flow(skill_name="document_parser") == "ocr_analysis"


@pytest.mark.unit
def test_infer_flow_node_signal_takes_precedence_over_default() -> None:
    assert infer_flow(node_name="ocr_node") == "ocr_analysis"
    assert infer_flow(node_name="route") == "conversation"


@pytest.mark.unit
def test_infer_flow_combined_signals() -> None:
    """Un seul signal OCR suffit (OR logique)."""
    assert (
        infer_flow(page_route="/chat", skill_name="ocr_extract", node_name="route")
        == "ocr_analysis"
    )


@pytest.mark.integration
def test_record_step_rejects_invalid_flow() -> None:
    """``record_step`` lève ValueError si le flow n'est pas dans le CHECK DB."""
    from uuid import uuid4

    from app.agent.repository import record_step

    with pytest.raises(ValueError, match="flow invalide"):
        record_step(
            None,  # type: ignore[arg-type]
            run_id=uuid4(),
            account_id=uuid4(),
            node_name="route",
            latency_ms=10,
            flow="invalid_flow_value",
        )
