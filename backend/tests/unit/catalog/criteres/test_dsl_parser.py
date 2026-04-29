"""F09 T044 — Parser/Evaluator DSL : 11 opérateurs + tri-state."""

from __future__ import annotations

from app.catalog.criteres.dsl import evaluate, parse


def test_var_const():
    expr = {"eq": [{"var": "x"}, {"const": 10}]}
    parse(expr)
    assert evaluate(expr, {"x": 10}) is True
    assert evaluate(expr, {"x": 5}) is False
    # missing var → None (undecidable)
    assert evaluate(expr, {}) is None


def test_neq():
    expr = {"neq": [{"var": "x"}, {"const": 1}]}
    assert evaluate(expr, {"x": 2}) is True
    assert evaluate(expr, {"x": 1}) is False


def test_gt_gte_lt_lte():
    assert evaluate({"gt": [{"var": "n"}, {"const": 5}]}, {"n": 6}) is True
    assert evaluate({"gte": [{"var": "n"}, {"const": 5}]}, {"n": 5}) is True
    assert evaluate({"lt": [{"var": "n"}, {"const": 5}]}, {"n": 4}) is True
    assert evaluate({"lte": [{"var": "n"}, {"const": 5}]}, {"n": 5}) is True


def test_in_operator():
    expr = {"in": [{"var": "country"}, {"const": ["FR", "CI", "SN"]}]}
    assert evaluate(expr, {"country": "CI"}) is True
    assert evaluate(expr, {"country": "US"}) is False
    assert evaluate(expr, {}) is None


def test_and_or_not():
    expr = {
        "and": [
            {"gt": [{"var": "score"}, {"const": 50}]},
            {"in": [{"var": "country"}, {"const": ["CI"]}]},
        ]
    }
    assert evaluate(expr, {"score": 70, "country": "CI"}) is True
    assert evaluate(expr, {"score": 30, "country": "CI"}) is False
    assert evaluate({"or": [{"const": False}, {"const": True}]}, {}) is True
    assert evaluate({"not": {"const": False}}, {}) is True


def test_tri_state_and_short_circuit_false():
    # AND with one False and one missing → False (because False short-circuits).
    expr = {"and": [{"const": False}, {"var": "missing"}]}
    assert evaluate(expr, {}) is False


def test_tri_state_or_short_circuit_true():
    expr = {"or": [{"const": True}, {"var": "missing"}]}
    assert evaluate(expr, {}) is True


def test_type_mismatch_returns_none():
    # Comparing string to int → undecidable.
    expr = {"gt": [{"var": "x"}, {"const": 1}]}
    assert evaluate(expr, {"x": "abc"}) is None
