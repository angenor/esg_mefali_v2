"""F08 — Enregistrement des EntitySpec dans le registry F06."""

from __future__ import annotations

from typing import Any

from app.admin.registry import EntitySpec, registry


def _sources_from_array(row: dict[str, Any]) -> list[str]:
    arr = row.get("source_ids") or []
    return [str(s) for s in arr]


def _source_from_single(row: dict[str, Any]) -> list[str]:
    sid = row.get("source_id")
    return [str(sid)] if sid else []


def register_f08_specs() -> None:
    """Idempotent — appelé au boot main.py."""
    if registry.get("fonds_source") is None:
        registry.register(
            EntitySpec(
                name="fonds_source",
                table="fonds_source",
                sources_relation=_sources_from_array,
                # Global /admin/search currently hardcodes (name, publisher, external_id)
                # so we leave searchable_fields empty for F08 entities — they have
                # dedicated list endpoints under /admin/fonds, /admin/intermediaires.
                searchable_fields=(),
                sidebar_section="catalog",
            )
        )
    if registry.get("intermediaire") is None:
        registry.register(
            EntitySpec(
                name="intermediaire",
                table="intermediaire",
                sources_relation=_sources_from_array,
                searchable_fields=(),
                sidebar_section="catalog",
            )
        )
    if registry.get("accreditation") is None:
        registry.register(
            EntitySpec(
                name="accreditation",
                table="accreditation",
                sources_relation=_source_from_single,
                searchable_fields=(),
                sidebar_section="catalog",
            )
        )
    if registry.get("offre") is None:
        registry.register(
            EntitySpec(
                name="offre",
                table="offre",
                sources_relation=_sources_from_array,
                searchable_fields=(),
                sidebar_section="catalog",
            )
        )


# Auto-register on import.
register_f08_specs()
