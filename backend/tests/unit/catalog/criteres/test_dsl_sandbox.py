"""F09 T045 — DSL fuzzing négatif (sandbox NFR-002)."""

from __future__ import annotations

import pytest

from app.catalog.criteres.dsl import DSLError, parse


def test_unknown_operator_rejected():
    with pytest.raises(DSLError, match="unknown operator"):
        parse({"exec": ["rm", "-rf"]})


def test_depth_exceeded():
    # Build a deeply nested expr (depth 8 > 6).
    node: dict = {"var": "x"}
    for _ in range(8):
        node = {"not": node}
    with pytest.raises(DSLError, match="depth"):
        parse(node)


def test_payload_too_large():
    big = {"or": [{"eq": [{"var": f"v{i}"}, {"const": "x" * 200}]} for i in range(40)]}
    with pytest.raises(DSLError, match="payload too large"):
        parse(big)


def test_multiple_keys_rejected():
    with pytest.raises(DSLError, match="exactly one operator"):
        parse({"eq": [{"var": "a"}, {"const": 1}], "and": []})


def test_invalid_in_right_operand():
    with pytest.raises(DSLError, match="'in' right operand"):
        parse({"in": [{"var": "a"}, {"var": "b"}]})


def test_eval_injection_blocked():
    # Try to inject a Python __import__ string as an op key.
    with pytest.raises(DSLError):
        parse({"__import__": "os"})


def test_logical_op_requires_two_children():
    with pytest.raises(DSLError, match="≥2 children"):
        parse({"and": [{"const": True}]})


def test_comparison_requires_two_children():
    with pytest.raises(DSLError, match="exactly 2 children"):
        parse({"eq": [{"var": "a"}]})


def test_var_must_be_string():
    with pytest.raises(DSLError, match="non-empty string"):
        parse({"var": ""})


def test_const_must_be_primitive():
    with pytest.raises(DSLError, match="primitive"):
        parse({"const": [1, 2]})
