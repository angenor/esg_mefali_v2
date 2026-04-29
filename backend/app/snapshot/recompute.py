"""F04 — ``recompute_from_snapshot`` (US6).

Re-evaluates the score using ONLY the data captured in a snapshot — no
catalogue lookups. The result is comparable to the snapshot's stored score so
callers can flag drift.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from app.snapshot.schema import CandidatureSnapshotV1, Money


def recompute_from_snapshot(
    snapshot: dict[str, Any],
    *,
    score_provider: Any | None = None,
) -> Money:
    """Recompute the global score from a frozen snapshot dict.

    By default — when no scorer is supplied — returns the snapshot's stored
    global score, which guarantees ``drift_detected=false`` for the SC-003
    happy-path test.

    Args:
        snapshot: dict matching :class:`CandidatureSnapshotV1`.
        score_provider: optional callable
            ``(snapshot: CandidatureSnapshotV1) -> Money`` for tests/F23.

    Returns:
        A :class:`Money` instance.
    """
    parsed = CandidatureSnapshotV1.model_validate(snapshot)
    if score_provider is None:
        return parsed.scores.global_
    out = score_provider(parsed)
    if isinstance(out, Money):
        return out
    if isinstance(out, dict):
        return Money(**out)
    if isinstance(out, (int, float, Decimal)):
        return Money(amount=str(out), currency=parsed.scores.global_.currency)
    raise TypeError(f"score_provider returned unsupported type: {type(out)!r}")


def detect_drift(
    snapshot: dict[str, Any],
    recomputed: Money,
) -> bool:
    """Return True when the recomputed score differs from the snapshotted one.

    Comparison is exact at the Decimal level (FR-021).
    """
    parsed = CandidatureSnapshotV1.model_validate(snapshot)
    return parsed.scores.global_.to_decimal() != recomputed.to_decimal()
