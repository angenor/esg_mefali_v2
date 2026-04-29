"""Tests F16 — show_kpi_card."""

from __future__ import annotations

from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.orchestrator.tool_registry import TOOL_REGISTRY
from app.orchestrator.tools.show_kpi_card import (
    ShowKpiCardPayload,
    register,
)


def _payload(**overrides: object) -> dict[str, object]:
    base: dict[str, object] = {
        "label": "Empreinte 2025",
        "value": "45.00",
        "unit": "tCO2e",
        "delta": {"value": "-12.0", "period": "vs 2024"},
        "source_ids": [42],
        "alt_text": "Empreinte carbone 2025.",
    }
    base.update(overrides)
    return base


def test_register_adds_tool() -> None:
    register()
    assert "show_kpi_card" in TOOL_REGISTRY


def test_basic_payload_ok() -> None:
    p = ShowKpiCardPayload(**_payload())
    assert p.value == Decimal("45.00")
    assert p.delta is not None
    assert p.delta.value == Decimal("-12.0")


def test_payload_without_delta_ok() -> None:
    p = ShowKpiCardPayload(**_payload(delta=None))
    assert p.delta is None


def test_value_serialised_as_string_in_json() -> None:
    p = ShowKpiCardPayload(**_payload())
    dumped = p.model_dump(mode="json")
    assert isinstance(dumped["value"], str)
    assert dumped["value"] == "45.00"


def test_xss_in_label_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowKpiCardPayload(**_payload(label="<script>x</script>"))


def test_xss_in_unit_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowKpiCardPayload(**_payload(unit="t<x>"))


def test_xss_in_period_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowKpiCardPayload(
            **_payload(delta={"value": "1", "period": "<x>"})
        )


def test_source_ids_empty_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowKpiCardPayload(**_payload(source_ids=[]))


def test_alt_text_empty_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowKpiCardPayload(**_payload(alt_text=""))


def test_extra_field_rejected() -> None:
    with pytest.raises(ValidationError):
        ShowKpiCardPayload(**_payload(extra_field="x"))


def test_label_max_length() -> None:
    with pytest.raises(ValidationError):
        ShowKpiCardPayload(**_payload(label="x" * 129))
