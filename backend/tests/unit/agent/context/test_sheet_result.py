"""F54 / T057 — Tests unitaires extract_sheet_result + render_sheet_result_note."""

from __future__ import annotations

import json

import pytest

from app.agent.context.sheet_result import (
    extract_sheet_result,
    render_sheet_result_note,
)


@pytest.mark.unit
class TestExtractSheetResult:
    def test_valid_ask_qcu(self) -> None:
        msg = {
            "role": "user",
            "content": "",
            "payload_json": {
                "sheet_result": {
                    "tool": "ask_qcu",
                    "value": "SARL",
                    "label": "Quelle est votre forme juridique ?",
                }
            },
        }
        out = extract_sheet_result(msg)
        assert out == {
            "tool": "ask_qcu",
            "value": "SARL",
            "label": "Quelle est votre forme juridique ?",
        }

    def test_valid_ask_form_with_payload(self) -> None:
        msg = {
            "payload_json": {
                "sheet_result": {
                    "tool": "ask_form",
                    "value": "submitted",
                    "label": "Profil entreprise",
                    "payload": {"raison_sociale": "Sankore", "effectif": 25},
                }
            }
        }
        out = extract_sheet_result(msg)
        assert out is not None
        assert out["payload"] == {"raison_sociale": "Sankore", "effectif": 25}

    def test_payload_json_serialized_as_string(self) -> None:
        msg = {
            "payload_json": json.dumps(
                {
                    "sheet_result": {
                        "tool": "ask_qcu",
                        "value": 5,
                        "label": "Note ?",
                    }
                }
            )
        }
        out = extract_sheet_result(msg)
        assert out is not None
        assert out["value"] == 5

    def test_none_message_returns_none(self) -> None:
        assert extract_sheet_result(None) is None

    def test_no_payload_json(self) -> None:
        assert extract_sheet_result({"content": "hi"}) is None

    def test_payload_without_sheet_result(self) -> None:
        assert extract_sheet_result({"payload_json": {"foo": "bar"}}) is None

    def test_invalid_sheet_result_missing_tool(self) -> None:
        msg = {"payload_json": {"sheet_result": {"value": "X", "label": "L"}}}
        assert extract_sheet_result(msg) is None

    def test_invalid_sheet_result_missing_value(self) -> None:
        msg = {"payload_json": {"sheet_result": {"tool": "t", "label": "L"}}}
        assert extract_sheet_result(msg) is None

    def test_invalid_sheet_result_value_none(self) -> None:
        msg = {
            "payload_json": {
                "sheet_result": {"tool": "t", "value": None, "label": "L"}
            }
        }
        assert extract_sheet_result(msg) is None

    def test_invalid_payload_extra_drops_silently(self) -> None:
        msg = {
            "payload_json": {
                "sheet_result": {
                    "tool": "t",
                    "value": "v",
                    "label": "L",
                    "payload": "not-a-dict",  # ignoré.
                }
            }
        }
        out = extract_sheet_result(msg)
        assert out is not None
        assert "payload" not in out


@pytest.mark.unit
class TestRenderSheetResultNote:
    def test_simple_render(self) -> None:
        sheet = {"tool": "ask_qcu", "value": "SARL", "label": "Forme ?"}
        out = render_sheet_result_note(sheet)
        assert out is not None
        assert "ask_qcu" in out
        assert "SARL" in out
        assert "Ne re-pose pas" in out

    def test_render_with_payload(self) -> None:
        sheet = {
            "tool": "ask_form",
            "value": "submitted",
            "label": "Profil",
            "payload": {"effectif": 25},
        }
        out = render_sheet_result_note(sheet)
        assert out is not None
        assert "effectif" in out
        assert "25" in out

    def test_none_returns_none(self) -> None:
        assert render_sheet_result_note(None) is None

    def test_value_with_curly_braces_is_escaped(self) -> None:
        # Escape FR-013 sur ``value``.
        sheet = {"tool": "t", "value": "{exploit}", "label": "L"}
        out = render_sheet_result_note(sheet)
        assert out is not None
        assert "{{exploit}}" in out

    def test_numeric_value_formatted(self) -> None:
        sheet = {"tool": "t", "value": 42, "label": "L"}
        out = render_sheet_result_note(sheet)
        assert out is not None
        assert "42" in out
