"""F35 — Tests pour le post-processeur (chips + unsourced_warning)."""

from __future__ import annotations

import pytest

from app.llm.post_processor import (
    DEFAULT_PATTERNS_PATH,
    PostProcessSignal,
    load_patterns,
    post_process,
)


@pytest.fixture()
def patterns():
    load_patterns.cache_clear()  # type: ignore[attr-defined]
    return load_patterns(str(DEFAULT_PATTERNS_PATH))


@pytest.mark.unit
def test_empty_response_returns_no_signal(patterns) -> None:
    assert post_process("", [], patterns) == []
    assert post_process(None, [], patterns) == []
    assert post_process("   ", [], patterns) == []


@pytest.mark.unit
def test_numbered_enumeration_emits_chips(patterns) -> None:
    text = "Voici vos options :\n1. Option A\n2. Option B\n3. Option C"
    signals = post_process(text, [], patterns)
    types = [s.type for s in signals]
    assert "chips_suggestion" in types
    chips = next(s for s in signals if s.type == "chips_suggestion")
    options = chips.payload["options"]
    assert len(options) >= 3
    assert any("Option A" in o for o in options)


@pytest.mark.unit
def test_binary_choice_emits_chips(patterns) -> None:
    text = "Preferez-vous SARL, SA ou SAS ?"
    signals = post_process(text, [], patterns)
    types = [s.type for s in signals]
    assert "chips_suggestion" in types


@pytest.mark.unit
def test_bullets_enumeration_emits_chips(patterns) -> None:
    text = "Choix :\n- Premier\n- Deuxieme\n- Troisieme"
    signals = post_process(text, [], patterns)
    chips = [s for s in signals if s.type == "chips_suggestion"]
    assert chips, "expected chips_suggestion from bullet list"


@pytest.mark.unit
def test_unsourced_number_emits_warning(patterns) -> None:
    text = "Le seuil minimum est de 50 000 FCFA pour acceder a ce dispositif."
    signals = post_process(text, [], patterns)
    warns = [s for s in signals if s.type == "unsourced_warning"]
    assert len(warns) == 1
    assert "FCFA" in warns[0].payload["matched_text"]


@pytest.mark.unit
def test_unsourced_percentage_emits_warning(patterns) -> None:
    text = "Le taux est de 25%."
    signals = post_process(text, [], patterns)
    warns = [s for s in signals if s.type == "unsourced_warning"]
    assert len(warns) == 1


@pytest.mark.unit
def test_with_cite_source_no_warning(patterns) -> None:
    text = "Le seuil est de 50 000 FCFA selon l'article L.1."
    tool_calls = [{"name": "cite_source", "arguments": {"source_id": "abc"}}]
    signals = post_process(text, tool_calls, patterns)
    warns = [s for s in signals if s.type == "unsourced_warning"]
    assert warns == []


@pytest.mark.unit
def test_with_cite_source_via_tool_name_key(patterns) -> None:
    text = "50 000 FCFA"
    tool_calls = [{"tool_name": "cite_source"}]
    signals = post_process(text, tool_calls, patterns)
    assert all(s.type != "unsourced_warning" for s in signals)


@pytest.mark.unit
def test_no_signal_for_pure_text(patterns) -> None:
    text = "Bonjour, je peux vous aider sur de nombreux sujets ESG."
    signals = post_process(text, [], patterns)
    assert signals == []


@pytest.mark.unit
def test_returns_signals_as_immutable_dataclasses(patterns) -> None:
    text = "1. A\n2. B\n3. C"
    signals = post_process(text, [], patterns)
    assert all(isinstance(s, PostProcessSignal) for s in signals)
    with pytest.raises((AttributeError, Exception)):
        signals[0].type = "other"  # type: ignore[misc]


@pytest.mark.unit
def test_load_patterns_fallback_on_missing_file(tmp_path) -> None:
    load_patterns.cache_clear()  # type: ignore[attr-defined]
    p = load_patterns(str(tmp_path / "missing.json"))
    assert len(p.enumeration) >= 1
    assert len(p.number_with_unit) >= 1


@pytest.mark.unit
def test_load_patterns_fallback_on_invalid_json(tmp_path) -> None:
    load_patterns.cache_clear()  # type: ignore[attr-defined]
    bad = tmp_path / "bad.json"
    bad.write_text("not json", encoding="utf-8")
    p = load_patterns(str(bad))
    assert len(p.number_with_unit) >= 1


@pytest.mark.unit
def test_load_patterns_fallback_on_non_dict(tmp_path) -> None:
    load_patterns.cache_clear()  # type: ignore[attr-defined]
    f = tmp_path / "list.json"
    f.write_text("[1, 2, 3]", encoding="utf-8")
    p = load_patterns(str(f))
    assert len(p.number_with_unit) >= 1
