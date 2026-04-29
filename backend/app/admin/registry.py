"""F06 — Entity registry : declarative spec for all admin-managed catalog entities.

F06 enregistre ``demo_indicator``. F07-F20 ajouteront les entités réelles via
``registry.register(spec)``.
"""

from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class EntitySpec:
    """Describe how to expose a catalog entity through the admin CRUD router."""

    name: str
    table: str  # SQL table name (we operate at the SQL level for portability).
    pk_column: str = "id"
    version_column: str = "version"
    created_at_column: str = "created_at"
    status_column: str = "status"
    sources_relation: Callable[[dict[str, Any]], Iterable[str]] | None = None
    """Returns iterable of source UUIDs related to a given row dict."""
    searchable_fields: tuple[str, ...] = ("name", "publisher", "external_id")
    sidebar_section: str = ""
    selectable_columns: tuple[str, ...] = ()
    """Columns to project on list/get; empty = ``*``."""


class EntityRegistry:
    """In-memory map (singleton) of registered ``EntitySpec``."""

    def __init__(self) -> None:
        self._items: dict[str, EntitySpec] = {}

    def register(self, spec: EntitySpec) -> None:
        if spec.name in self._items:
            raise ValueError(f"Entity already registered: {spec.name}")
        self._items[spec.name] = spec

    def get(self, name: str) -> EntitySpec | None:
        return self._items.get(name)

    def all(self) -> list[EntitySpec]:
        return list(self._items.values())

    def clear(self) -> None:
        """Test helper — never call in prod code paths."""
        self._items.clear()


registry = EntityRegistry()
