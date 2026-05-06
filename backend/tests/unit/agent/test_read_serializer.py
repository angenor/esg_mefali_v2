"""F55 / T121 — Unit tests ``serialize_read_result``."""

from __future__ import annotations

import json

import pytest

from app.agent.read_serializer import estimate_tokens, serialize_read_result

pytestmark = pytest.mark.unit


def test_estimate_tokens_basic():
    assert estimate_tokens("a" * 4) == 1
    assert estimate_tokens("a" * 8) == 2


def test_serialize_dict_within_budget():
    payload = {"hits": [{"id": "1", "text": "alpha"}]}
    out = serialize_read_result(payload, budget_tokens=1500)
    parsed = json.loads(out)
    assert parsed["hits"][0]["id"] == "1"


def test_serialize_truncates_when_over_budget():
    big = {"text": "x" * 100000}
    out = serialize_read_result(big, budget_tokens=10)
    # Minimum char budget is 64 (lower bound)
    assert len(out) <= 256  # ~min budget + small overhead, well below 100000


def test_serialize_handles_list():
    payload = ["a", "b", "c"]
    out = serialize_read_result(payload, budget_tokens=100)
    parsed = json.loads(out)
    assert isinstance(parsed, list)


def test_serialize_string_payload():
    out = serialize_read_result("hello world", budget_tokens=100)
    assert "hello world" in out


def test_serialize_truncates_long_strings():
    out = serialize_read_result("a" * 10000, budget_tokens=10)
    # Min char budget = 64, so cap is in the low hundreds at most
    assert len(out) <= 200
    assert len(out) < 10000


def test_serialize_nested_structure():
    payload = {"a": {"b": {"c": "deep"}}}
    out = serialize_read_result(payload, budget_tokens=200)
    parsed = json.loads(out)
    assert parsed["a"]["b"]["c"] == "deep"
