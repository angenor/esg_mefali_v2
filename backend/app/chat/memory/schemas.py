"""F57 — Pydantic schemas pour les endpoints ``/me/chat/threads/{id}/memory``.

Référence : ``specs/057-agent-memory-rag/contracts/memory-endpoint.md`` et
``data-model.md`` §4.2.

Backwards-compatible avec F18 : champs ajoutés, pas renommés. La réponse
historique F18 reste un sous-ensemble de ``MemorySnapshotV2``.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class EntityRef(BaseModel):
    """Référence à une entité business mentionnée dans le thread."""

    model_config = ConfigDict(extra="forbid")

    type: Literal["Entreprise", "Projet", "Candidature", "Indicateur"]
    id: UUID
    label: str = Field(min_length=0, max_length=200)


class MemorySnapshotV2(BaseModel):
    """GET /me/chat/threads/{id}/memory — payload réponse (FR-007)."""

    model_config = ConfigDict(extra="forbid")

    total_messages: int = Field(ge=0)
    recent_messages_count: int = Field(ge=0)
    summary: str | None = None
    vector_index_size: int = Field(ge=0)
    last_compaction_at: datetime | None = None
    entities_referenced: list[EntityRef] = Field(default_factory=list)


class ForgetMemoryResult(BaseModel):
    """DELETE /me/chat/threads/{id}/memory — payload réponse (FR-008)."""

    model_config = ConfigDict(extra="forbid")

    thread_id: UUID
    embeddings_purged: int = Field(ge=0)
    summary_cleared: bool
    last_compaction_cleared: bool
    messages_kept_for_audit: int = Field(ge=0)
    agent_entity_memory_unchanged: bool = True
    audit_log_id: UUID | None = None


__all__ = [
    "EntityRef",
    "ForgetMemoryResult",
    "MemorySnapshotV2",
]
