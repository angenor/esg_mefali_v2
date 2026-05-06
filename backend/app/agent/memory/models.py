"""F57 — ORM models pour les nouvelles tables ``agent_entity_memory`` et
``recall_log``.

Référence : ``specs/057-agent-memory-rag/data-model.md`` §4.1.

Pour le MVP F57, les requêtes mémoire critiques (cosine search, UPSERT
entity_memory) restent en SQL brut (text(...)) pour éviter la complexité
ORM autour de pgvector + ON CONFLICT … DO UPDATE. Ces ORM models servent
surtout aux tests et à l'introspection.
"""

from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import (
    TIMESTAMP,
    CheckConstraint,
    ForeignKey,
    Integer,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.models import Base


class AgentEntityMemory(Base):
    """Stocke un fait stable par account et par entité business (US7)."""

    __tablename__ = "agent_entity_memory"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("account.id", ondelete="CASCADE"),
        nullable=False,
    )
    entity_type: Mapped[str] = mapped_column(Text, nullable=False)
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    summary: Mapped[str] = mapped_column(Text, nullable=False)
    sources_used: Mapped[list] = mapped_column(
        JSONB, nullable=False, server_default=text("'[]'::jsonb")
    )
    last_updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)

    __table_args__ = (
        UniqueConstraint(
            "account_id",
            "entity_type",
            "entity_id",
            name="uq_agent_entity_memory_account_entity",
        ),
    )


class RecallLog(Base):
    """Trace toutes les opérations de recall (auto + tool) — append-only (P3)."""

    __tablename__ = "recall_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    agent_run_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("agent_run.id", ondelete="SET NULL"),
        nullable=True,
    )
    account_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("account.id", ondelete="CASCADE"),
        nullable=False,
    )
    thread_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_thread.id", ondelete="CASCADE"),
        nullable=False,
    )
    recall_type: Mapped[str] = mapped_column(Text, nullable=False)
    query_hash: Mapped[str] = mapped_column(Text, nullable=False)
    top_k: Mapped[int] = mapped_column(Integer, nullable=False)
    top_scores: Mapped[list] = mapped_column(JSONB, nullable=False)
    latency_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        CheckConstraint(
            "recall_type IN ('auto', 'tool')", name="recall_log_recall_type_check"
        ),
    )


__all__ = ["AgentEntityMemory", "RecallLog"]
