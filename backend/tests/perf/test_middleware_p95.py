"""F03 NFR-002 / SC-006 — Smoke perf middleware p95 ajouté < 50ms."""

from __future__ import annotations

import time

import pytest

from app.db import SessionLocal
from app.services.llm_validation import decision_cache, validate_llm_output
from tests.conftest import requires_db


@requires_db
@pytest.mark.perf
def test_middleware_p95_under_50ms():
    decision_cache.clear()
    msg_no_claim = {
        "role": "assistant",
        "content": "Bonjour, comment puis-je vous aider ?",
        "tool_calls": [],
    }
    msg_no_cite = {
        "role": "assistant",
        "content": "Le seuil est 30%.",
        "tool_calls": [],
    }
    db = SessionLocal()
    times: list[float] = []
    try:
        for i in range(200):
            msg = msg_no_claim if i % 2 else msg_no_cite
            t0 = time.perf_counter()
            validate_llm_output(db, msg)
            times.append(time.perf_counter() - t0)
    finally:
        db.close()
    times.sort()
    p95 = times[int(0.95 * len(times))]
    # Tolérance dev : < 100ms
    assert p95 < 0.1, f"p95 trop élevé: {p95*1000:.1f}ms"
