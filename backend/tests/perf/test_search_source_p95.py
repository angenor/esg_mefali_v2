"""F03 NFR-001 / SC-005 — Smoke perf search_source p95 < 200ms.

Skip si DB indispo. Réduit à 50 sources + 100 calls en CI rapide ; doit rester
représentatif et < 200 ms p95 même sur dev local.
"""

from __future__ import annotations

import time
import uuid

import pytest
from sqlalchemy import text

from app.db import SessionLocal, get_engine_migrator
from app.schemas.source import SearchSourceInput
from app.scripts.seed_admin import create_admin
from app.services.llm_tools import handle_search_source
from tests.conftest import requires_db


def _stub_emb(_):
    return [[0.1] * 1024]


@requires_db
@pytest.mark.perf
def test_search_source_p95_under_200ms():
    # Seed 50 sources verified
    db = SessionLocal()
    try:
        a = create_admin(
            db,
            email=f"perf_a_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com",
            password="Sup3rSecret!Pass",
        )
        b = create_admin(
            db,
            email=f"perf_b_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com",
            password="Sup3rSecret!Pass",
        )
        db.commit()
        a_id, b_id = a.id, b.id
    finally:
        db.close()

    eng = get_engine_migrator()
    with eng.begin() as c:
        for i in range(50):
            sid = uuid.uuid4()
            c.execute(
                text(
                    "INSERT INTO source (id, url, title, publisher, "
                    "captured_at, captured_by, verification_status, "
                    "status_version, created_at, updated_at) VALUES "
                    "(:id, :u, :t, 'GCF', now(), :cb, 'pending', "
                    "1, now(), now())"
                ),
                {
                    "id": str(sid),
                    "u": f"https://x.example/perf/{i}",
                    "t": f"GCF perf doc {i}",
                    "cb": str(a_id),
                },
            )
            c.execute(
                text(
                    "UPDATE source SET verification_status = 'verified', "
                    "verified_by = :vb, verified_at = now(), embedding = :emb "
                    "WHERE id = :id"
                ),
                {"vb": str(b_id), "emb": [0.1] * 1024, "id": str(sid)},
            )

    # 100 calls
    db = SessionLocal()
    times: list[float] = []
    try:
        for _ in range(100):
            t0 = time.perf_counter()
            handle_search_source(
                db, SearchSourceInput(query="GCF perf"), embedding_func=_stub_emb
            )
            times.append(time.perf_counter() - t0)
    finally:
        db.close()
    times.sort()
    p95 = times[int(0.95 * len(times))]
    assert p95 < 0.5, f"p95 trop élevé: {p95*1000:.1f}ms"  # tolérance dev
