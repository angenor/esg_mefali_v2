"""F10 — TTLCache primitive unit tests."""

from __future__ import annotations

from app.admin.services import dashboard_stats as ds


def test_get_or_compute_caches_value() -> None:
    ds.invalidate()
    calls = {"n": 0}

    def compute() -> int:
        calls["n"] += 1
        return 42

    assert ds.get_or_compute("k1", compute) == 42
    assert ds.get_or_compute("k1", compute) == 42
    assert calls["n"] == 1
    assert ds.cache_size() == 1


def test_invalidate_clears_key() -> None:
    ds.invalidate()
    ds.get_or_compute("k1", lambda: 1)
    ds.get_or_compute("k2", lambda: 2)
    ds.invalidate("k1")
    assert ds.cache_size() == 1
    ds.invalidate()
    assert ds.cache_size() == 0
