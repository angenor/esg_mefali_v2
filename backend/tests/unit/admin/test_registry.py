"""F06 T057 — Unit tests for EntityRegistry."""

from __future__ import annotations

import pytest

from app.admin.registry import EntityRegistry, EntitySpec


def test_register_and_get():
    reg = EntityRegistry()
    spec = EntitySpec(name="x", table="x")
    reg.register(spec)
    assert reg.get("x") is spec
    assert reg.get("missing") is None


def test_duplicate_register_raises():
    reg = EntityRegistry()
    spec = EntitySpec(name="x", table="x")
    reg.register(spec)
    with pytest.raises(ValueError):
        reg.register(spec)


def test_all_returns_registered_items():
    reg = EntityRegistry()
    reg.register(EntitySpec(name="a", table="a"))
    reg.register(EntitySpec(name="b", table="b"))
    names = {s.name for s in reg.all()}
    assert names == {"a", "b"}


def test_global_registry_has_demo_indicator():
    """Boot side-effect: catalog import registers demo_indicator."""
    import app.catalog  # noqa: F401
    from app.admin.registry import registry

    spec = registry.get("demo_indicator")
    assert spec is not None
    assert spec.table == "demo_indicator"
    assert spec.sources_relation is not None
