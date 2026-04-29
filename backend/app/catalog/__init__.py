"""F06 — Catalog entity registrations.

Importing this module registers all catalog entities with the global
``EntityRegistry``. Idempotent (safe re-imports).
"""

from __future__ import annotations

from typing import Any

from app.admin.registry import EntitySpec, registry


def _demo_indicator_sources(row: dict) -> list[str]:
    sid = row.get("source_id")
    return [str(sid)] if sid else []


def _f09_sources_via_cache(row: dict[str, Any]) -> list[str]:
    """F09 indicateur/referentiel : sources via junction table.

    Resolved at publish-time by service layer which injects ``_source_ids``
    into the row dict before calling ``verify_sources_or_422``.
    """
    cached = row.get("_source_ids")
    if cached is not None:
        return [str(s) for s in cached]
    return []


def _f09_sources_single(row: dict[str, Any]) -> list[str]:
    sid = row.get("source_id")
    return [str(sid)] if sid else []


_DEMO_INDICATOR_SPEC = EntitySpec(
    name="demo_indicator",
    table="demo_indicator",
    sources_relation=_demo_indicator_sources,
    searchable_fields=("name", "publisher", "external_id"),
    sidebar_section="Indicateurs (démo)",
)


def register_f09_specs() -> None:
    """Register F09 entities (idempotent)."""
    if registry.get("indicateur") is None:
        registry.register(
            EntitySpec(
                name="indicateur",
                table="indicateur",
                sources_relation=_f09_sources_via_cache,
                searchable_fields=(),
                sidebar_section="catalog",
            )
        )
    if registry.get("referentiel") is None:
        registry.register(
            EntitySpec(
                name="referentiel",
                table="referentiel",
                sources_relation=_f09_sources_via_cache,
                searchable_fields=(),
                sidebar_section="catalog",
            )
        )
    if registry.get("critere") is None:
        registry.register(
            EntitySpec(
                name="critere",
                table="critere",
                sources_relation=_f09_sources_single,
                searchable_fields=(),
                sidebar_section="catalog",
            )
        )
    if registry.get("document_requis") is None:
        registry.register(
            EntitySpec(
                name="document_requis",
                table="document_requis",
                sources_relation=_f09_sources_single,
                searchable_fields=(),
                sidebar_section="catalog",
            )
        )
    if registry.get("facteur_emission") is None:
        registry.register(
            EntitySpec(
                name="facteur_emission",
                table="facteur_emission",
                sources_relation=_f09_sources_single,
                searchable_fields=(),
                sidebar_section="catalog",
            )
        )


def register_all() -> None:
    if registry.get("demo_indicator") is None:
        registry.register(_DEMO_INDICATOR_SPEC)
    register_f09_specs()


register_all()
