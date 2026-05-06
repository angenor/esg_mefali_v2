"""F58 / T054 — Tests unitaires loop_detector (FR-016)."""

from __future__ import annotations

import pytest

from app.agent.guardrails.loop_detector import (
    LoopDetectionResult,
    args_hash,
    detect_loop,
)


def _call(_name: str, **args):
    return {"name": _name, "arguments": args}


@pytest.mark.unit
def test_no_loop_empty_history() -> None:
    res = detect_loop([], _call("create_project", name="A"))
    assert res.triggered is False
    assert res.reason == "none"


@pytest.mark.unit
def test_no_loop_single_call() -> None:
    history = [_call("create_project", name="A")]
    res = detect_loop(history, _call("create_project", name="B"))
    assert res.triggered is False


@pytest.mark.unit
def test_loop_detected_3x_identical_args() -> None:
    history = [
        _call("create_project", name="A", region="CI"),
        _call("create_project", name="A", region="CI"),
    ]
    new = _call("create_project", name="A", region="CI")
    res = detect_loop(history, new)
    assert res.triggered is True
    assert res.reason == "identical_args_3x"


@pytest.mark.unit
def test_no_loop_3x_different_args_cite_source() -> None:
    history = [
        _call("cite_source", source_id="S1"),
        _call("cite_source", source_id="S2"),
    ]
    new = _call("cite_source", source_id="S3")
    res = detect_loop(history, new)
    assert res.triggered is False


@pytest.mark.unit
def test_loop_too_many_calls_in_turn() -> None:
    # Génère 10 appels variés non-loopants
    history = [_call("show", id=str(i)) for i in range(10)]
    new = _call("create_project", name="X")
    res = detect_loop(history, new, max_per_turn=10)
    assert res.triggered is True
    assert res.reason == "too_many_calls"


@pytest.mark.unit
def test_no_loop_just_under_max_per_turn() -> None:
    history = [_call("show", id=str(i)) for i in range(9)]
    new = _call("show", id="last")
    res = detect_loop(history, new, max_per_turn=10)
    assert res.triggered is False


@pytest.mark.unit
def test_args_hash_deterministic() -> None:
    h1 = args_hash({"a": 1, "b": "x"})
    h2 = args_hash({"b": "x", "a": 1})  # ordre différent → même hash
    assert h1 == h2


@pytest.mark.unit
def test_args_hash_different_for_different_args() -> None:
    h1 = args_hash({"a": 1})
    h2 = args_hash({"a": 2})
    assert h1 != h2


@pytest.mark.unit
def test_args_hash_handles_complex_types() -> None:
    from datetime import UTC, datetime
    from uuid import uuid4

    # default=str doit gérer UUID/datetime sans erreur
    h = args_hash({"id": uuid4(), "ts": datetime.now(UTC), "list": [1, 2]})
    assert isinstance(h, str)
    assert len(h) == 64  # SHA256 hex


@pytest.mark.unit
def test_loop_detection_result_is_immutable() -> None:
    res = LoopDetectionResult(
        triggered=False,
        reason="none",
        last_tool_name=None,
        last_args_hash=None,
    )
    from dataclasses import FrozenInstanceError

    with pytest.raises(FrozenInstanceError):
        res.triggered = True  # type: ignore[misc]
