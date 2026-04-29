"""F09 US3 — DSL JSON sandboxé pour critères ESG.

Format strict :
- racine = un opérateur (dict avec exactement une clé d'opérateur).
- 11 opérateurs supportés (cf research) : ``and``, ``or``, ``not``, ``eq``, ``neq``,
  ``gt``, ``gte``, ``lt``, ``lte``, ``in``, ``var``.
- profondeur ≤ 6 (NFR-002).
- payload sérialisé ≤ 8 KB.
- aucun ``eval``/code dynamique.
- évaluation tri-state : ``True`` / ``False`` / ``None`` (undecidable, var manquante).
"""

from __future__ import annotations

import json
from typing import Any

MAX_DEPTH = 6
MAX_PAYLOAD_BYTES = 8 * 1024
LOGICAL_OPS = {"and", "or", "not"}
COMPARISON_OPS = {"eq", "neq", "gt", "gte", "lt", "lte", "in"}
LEAF_OPS = {"var", "const"}
ALLOWED_OPS = LOGICAL_OPS | COMPARISON_OPS | LEAF_OPS


class DSLError(ValueError):
    """Raised on parser/validation errors."""


def _check_payload_size(expression: dict[str, Any]) -> None:
    raw = json.dumps(expression, separators=(",", ":")).encode("utf-8")
    if len(raw) > MAX_PAYLOAD_BYTES:
        raise DSLError(f"payload too large: {len(raw)} bytes > {MAX_PAYLOAD_BYTES}")


def _validate_node(node: Any, depth: int) -> None:
    if depth > MAX_DEPTH:
        raise DSLError(f"depth > {MAX_DEPTH}")
    if not isinstance(node, dict):
        raise DSLError("each node must be an object")
    if len(node) != 1:
        raise DSLError("each node must have exactly one operator key")
    (op, val) = next(iter(node.items()))
    if op not in ALLOWED_OPS:
        raise DSLError(f"unknown operator: {op!r}")
    if op == "var":
        if not isinstance(val, str) or not val:
            raise DSLError("'var' value must be a non-empty string")
        return
    if op == "const":
        # primitive only.
        if isinstance(val, list | dict):
            raise DSLError("'const' value must be a primitive")
        return
    if op == "not":
        _validate_node(val, depth + 1)
        return
    if op in {"and", "or"}:
        if not isinstance(val, list) or len(val) < 2:
            raise DSLError(f"{op!r} requires a list of ≥2 children")
        for child in val:
            _validate_node(child, depth + 1)
        return
    # comparison ops: list of 2 children
    if not isinstance(val, list) or len(val) != 2:
        raise DSLError(f"{op!r} requires exactly 2 children")
    _validate_node(val[0], depth + 1)
    if op == "in":
        # right operand must be const list
        right = val[1]
        if not (isinstance(right, dict) and "const" in right and isinstance(right["const"], list)):
            raise DSLError("'in' right operand must be {'const': [...]}")
    else:
        _validate_node(val[1], depth + 1)


def parse(expression: dict[str, Any]) -> dict[str, Any]:
    """Validate the DSL payload. Returns the same dict on success.

    Raises ``DSLError`` on any violation.
    """
    if not isinstance(expression, dict):
        raise DSLError("expression must be an object")
    _check_payload_size(expression)
    _validate_node(expression, depth=1)
    return expression


def _eval_node(node: Any, context: dict[str, Any]) -> Any:
    """Evaluate an already-validated node. Returns Python value or ``None``."""
    (op, val) = next(iter(node.items()))
    if op == "const":
        return val
    if op == "var":
        return context.get(val, None)
    if op == "not":
        v = _eval_node(val, context)
        if v is None:
            return None
        return not bool(v)
    if op in {"and", "or"}:
        results = [_eval_node(c, context) for c in val]
        if op == "and":
            if any(r is False for r in results):
                return False
            if any(r is None for r in results):
                return None
            return all(bool(r) for r in results)
        # or
        if any(r is True for r in results):
            return True
        if any(r is None for r in results):
            return None
        return any(bool(r) for r in results)
    # comparison
    left = _eval_node(val[0], context)
    if op == "in":
        right = val[1]["const"]
        if left is None:
            return None
        return left in right
    right = _eval_node(val[1], context)
    if left is None or right is None:
        return None
    try:
        if op == "eq":
            return left == right
        if op == "neq":
            return left != right
        if op == "gt":
            return left > right
        if op == "gte":
            return left >= right
        if op == "lt":
            return left < right
        if op == "lte":
            return left <= right
    except TypeError:
        return None
    raise DSLError(f"unsupported op at runtime: {op}")


def evaluate(expression: dict[str, Any], context: dict[str, Any]) -> bool | None:
    """Tri-state evaluation. Returns True/False/None (undecidable)."""
    parse(expression)  # re-validate defensively (cheap).
    result = _eval_node(expression, context)
    if result is None:
        return None
    return bool(result)
