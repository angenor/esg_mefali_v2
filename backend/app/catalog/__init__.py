"""F06 — Catalog entity registrations.

Importing this module registers all catalog entities with the global
``EntityRegistry``. Idempotent (safe re-imports).
"""

from __future__ import annotations

from app.admin.registry import EntitySpec, registry


def _demo_indicator_sources(row: dict) -> list[str]:
    sid = row.get("source_id")
    return [str(sid)] if sid else []


_DEMO_INDICATOR_SPEC = EntitySpec(
    name="demo_indicator",
    table="demo_indicator",
    sources_relation=_demo_indicator_sources,
    searchable_fields=("name", "publisher", "external_id"),
    sidebar_section="Indicateurs (démo)",
)


def register_all() -> None:
    if registry.get("demo_indicator") is None:
        registry.register(_DEMO_INDICATOR_SPEC)


register_all()
