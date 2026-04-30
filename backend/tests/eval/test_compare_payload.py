"""F35 — Tests unitaires pour ``compare_payload``."""

from __future__ import annotations

import pytest

from app.eval.compare_payload import compare_payload


@pytest.mark.unit
def test_empty_expected_returns_match() -> None:
    ok, reason = compare_payload({}, {"foo": 1})
    assert ok is True
    assert reason is None


@pytest.mark.unit
def test_actual_none_with_constraints_fails() -> None:
    ok, reason = compare_payload({"options_count_min": 1}, None)
    assert ok is False
    assert reason == "actual_payload_missing"


@pytest.mark.unit
def test_options_count_min_ok() -> None:
    ok, _ = compare_payload(
        {"options_count_min": 2},
        {"options": [{"label": "A"}, {"label": "B"}, {"label": "C"}]},
    )
    assert ok is True


@pytest.mark.unit
def test_options_count_min_violated() -> None:
    ok, reason = compare_payload(
        {"options_count_min": 4}, {"options": [{"label": "A"}, {"label": "B"}]}
    )
    assert ok is False
    assert reason == "options_count_min_violated"


@pytest.mark.unit
def test_options_count_max_violated() -> None:
    ok, reason = compare_payload({"options_count_max": 1}, {"options": ["A", "B"]})
    assert ok is False
    assert reason == "options_count_max_violated"


@pytest.mark.unit
def test_options_contain_strings() -> None:
    ok, _ = compare_payload(
        {"options_contain": ["SARL", "SA"]},
        {"options": ["SARL unipersonnelle", "SA cotee", "SAS"]},
    )
    assert ok is True


@pytest.mark.unit
def test_options_contain_missing() -> None:
    ok, reason = compare_payload(
        {"options_contain": ["SARL", "SA"]}, {"options": ["EURL", "EI"]}
    )
    assert ok is False
    assert reason is not None and reason.startswith("options_contain_missing:")


@pytest.mark.unit
def test_options_contain_not_a_list() -> None:
    ok, reason = compare_payload({"options_contain": "SARL"}, {"options": []})
    assert ok is False
    assert reason == "options_contain_not_a_list"


@pytest.mark.unit
def test_equals_match() -> None:
    ok, _ = compare_payload({"equals": {"label": "X"}}, {"label": "X", "extra": 1})
    assert ok is True


@pytest.mark.unit
def test_equals_mismatch() -> None:
    ok, reason = compare_payload({"equals": {"label": "X"}}, {"label": "Y"})
    assert ok is False
    assert reason == "equals_mismatch:label"


@pytest.mark.unit
def test_equals_not_a_dict() -> None:
    ok, reason = compare_payload({"equals": "X"}, {})
    assert ok is False
    assert reason == "equals_not_a_dict"


@pytest.mark.unit
def test_regex_match() -> None:
    ok, _ = compare_payload({"regex": {"name": "^ACME"}}, {"name": "ACME SARL"})
    assert ok is True


@pytest.mark.unit
def test_regex_mismatch() -> None:
    ok, reason = compare_payload({"regex": {"name": "^XYZ"}}, {"name": "ABC"})
    assert ok is False
    assert reason == "regex_mismatch:name"


@pytest.mark.unit
def test_regex_field_missing() -> None:
    ok, reason = compare_payload({"regex": {"name": "^A"}}, {})
    assert ok is False
    assert reason == "regex_field_missing:name"


@pytest.mark.unit
def test_regex_invalid_pattern() -> None:
    ok, reason = compare_payload({"regex": {"name": "[invalid"}}, {"name": "X"})
    assert ok is False
    assert reason == "regex_invalid:name"


@pytest.mark.unit
def test_regex_not_a_dict() -> None:
    ok, reason = compare_payload({"regex": "x"}, {"name": "X"})
    assert ok is False
    assert reason == "regex_not_a_dict"


@pytest.mark.unit
def test_options_dict_with_text_key() -> None:
    ok, _ = compare_payload(
        {"options_contain": ["alpha"]},
        {"options": [{"text": "alpha-team"}, {"value": "beta"}]},
    )
    assert ok is True


@pytest.mark.unit
def test_options_invalid_payload_shape() -> None:
    ok, reason = compare_payload({"options_count_min": 1}, {"options": "not a list"})
    assert ok is False
    assert reason == "options_count_min_violated"
