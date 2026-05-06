"""F55 / T015 — Unit tests ``app.agent.sse.format_event``.

Vérifie le format SSE EventSource (event/data/id/double-newline) et le
préfixe ``dry_run:`` (US6).
"""

from __future__ import annotations

import json

import pytest

from app.agent.sse import format_event


class TestFormatEvent:
    @pytest.mark.unit
    def test_basic_text_delta(self):
        out = format_event("text_delta", {"delta": "hello", "message_id": "m1"})
        assert out.startswith("event: text_delta\n")
        assert "data: " in out
        assert out.endswith("\n\n")

    @pytest.mark.unit
    def test_payload_serialized_json(self):
        out = format_event("mutation", {"entity_type": "Project", "n": 42})
        # extraire la ligne data:
        data_line = next(
            line for line in out.splitlines() if line.startswith("data:")
        )
        payload = json.loads(data_line.removeprefix("data: "))
        assert payload["entity_type"] == "Project"
        assert payload["n"] == 42

    @pytest.mark.unit
    def test_event_id_included_when_provided(self):
        out = format_event("text_delta", {"delta": "x"}, event_id="evt_42")
        assert "id: evt_42\n" in out

    @pytest.mark.unit
    def test_no_id_line_when_omitted(self):
        out = format_event("text_delta", {"delta": "x"})
        assert "\nid:" not in out

    @pytest.mark.unit
    def test_dry_run_prefix(self):
        out = format_event("mutation", {"k": "v"}, dry_run=True)
        assert out.startswith("event: dry_run:mutation\n")

    @pytest.mark.unit
    def test_dry_run_false_no_prefix(self):
        out = format_event("mutation", {"k": "v"}, dry_run=False)
        assert out.startswith("event: mutation\n")

    @pytest.mark.unit
    def test_unicode_safe(self):
        out = format_event("text_delta", {"delta": "Bonjour é à ç"})
        assert "Bonjour é à ç" in out

    @pytest.mark.unit
    def test_empty_event_type_rejected(self):
        with pytest.raises(ValueError):
            format_event("", {})

    @pytest.mark.unit
    def test_double_newline_terminator(self):
        out = format_event("done", {"final_text": ""})
        assert out.count("\n\n") == 1
        # garantir que c'est bien à la fin
        assert out[-2:] == "\n\n"

    @pytest.mark.unit
    def test_serialize_uuid_via_default_str(self):
        from uuid import uuid4

        u = uuid4()
        out = format_event("mutation", {"entity_id": u})
        # default=str doit avoir converti
        assert str(u) in out
