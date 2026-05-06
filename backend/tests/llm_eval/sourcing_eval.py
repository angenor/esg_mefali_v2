"""F56 / T029 — Évaluation golden set du détecteur (FR-015 / NFR-003).

Charge ``tests/golden/sourcing.jsonl`` et calcule precision/recall sur la
détection de claims (``must_be_unsourced_strict`` ⇔ "claim factuel attendu").

Seuils CI bloquants :
- recall ≥ 0.90
- precision ≥ 0.85
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.agent.sourcing.detector import detect_claims


def _golden_path() -> Path:
    here = Path(__file__).resolve().parent
    return here.parent / "golden" / "sourcing.jsonl"


def _load_cases() -> list[dict]:
    p = _golden_path()
    cases: list[dict] = []
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        cases.append(json.loads(line))
    return cases


def _classify(case: dict) -> tuple[bool, bool]:
    """Retourne (predicted_factual, gold_factual) pour un cas."""
    text = case["text"]
    tool_outputs = case.get("tool_outputs", [])
    claims = detect_claims(text, tool_outputs=tool_outputs)
    # Considère factuel = il existe ≥ 1 claim NON from_tool
    has_real_claim = any(not c.from_tool for c in claims)
    gold = bool(case.get("must_be_unsourced_strict", False))
    return (has_real_claim, gold)


@pytest.mark.unit
def test_golden_set_loads_50_cases() -> None:
    cases = _load_cases()
    assert len(cases) >= 50, f"expected ≥50, got {len(cases)}"


@pytest.mark.unit
def test_golden_set_recall_and_precision() -> None:
    """recall ≥ 0.90, precision ≥ 0.85 — bloque CI sinon."""
    cases = _load_cases()
    tp = fp = fn = tn = 0
    for case in cases:
        predicted, gold = _classify(case)
        if predicted and gold:
            tp += 1
        elif predicted and not gold:
            fp += 1
        elif (not predicted) and gold:
            fn += 1
        else:
            tn += 1

    precision = tp / (tp + fp) if (tp + fp) else 1.0
    recall = tp / (tp + fn) if (tp + fn) else 1.0
    assert recall >= 0.90, f"recall={recall:.3f} < 0.90 (tp={tp} fn={fn})"
    assert precision >= 0.85, (
        f"precision={precision:.3f} < 0.85 (tp={tp} fp={fp})"
    )
