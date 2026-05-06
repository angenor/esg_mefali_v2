"""F53 — ORM SQLAlchemy pour ``agent_run`` et ``agent_run_step``.

Mappés sur les tables créées par la migration 0032. Append-only :
- ``app_user`` rôle a uniquement ``SELECT`` + ``INSERT`` ;
- l'unique ``UPDATE`` (complétion finale) passe par
  ``SET LOCAL ROLE app_admin`` côté runner (cf. data-model section 2).
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class _AgentBase(DeclarativeBase):
    """Base ORM dédiée à l'agent (n'interfère pas avec les autres modèles)."""


class AgentRun(_AgentBase):
    """Trace d'une exécution complète du graph (un row par tour de chat)."""

    __tablename__ = "agent_run"
    __table_args__ = (
        CheckConstraint(
            r"thread_id ~ '^[0-9a-f-]{36}:[0-9a-f-]{36}$'",
            name="agent_run_thread_id_format",
        ),
    )

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    user_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("account_user.id"), nullable=False
    )
    thread_id: Mapped[str] = mapped_column(String(128), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="ok"
    )
    total_latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    total_tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    retry_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    final_node: Mapped[str | None] = mapped_column(String(64), nullable=True)
    error_summary: Mapped[str | None] = mapped_column(Text, nullable=True)

    steps: Mapped[list[AgentRunStep]] = relationship(
        "AgentRunStep", back_populates="run", cascade="save-update"
    )


class AgentRunStep(_AgentBase):
    """Trace d'une exécution de nœud individuel."""

    __tablename__ = "agent_run_step"

    id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        server_default=func.gen_random_uuid(),
    )
    run_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True),
        ForeignKey("agent_run.id", ondelete="RESTRICT"),
        nullable=False,
    )
    account_id: Mapped[UUID] = mapped_column(
        PG_UUID(as_uuid=True), ForeignKey("account.id"), nullable=False
    )
    node_name: Mapped[str] = mapped_column(String(64), nullable=False)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now()
    )
    latency_ms: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_in: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tokens_out: Mapped[int | None] = mapped_column(Integer, nullable=True)
    tool_calls_count: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default="0"
    )
    status: Mapped[str] = mapped_column(
        String(16), nullable=False, server_default="ok"
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)

    run: Mapped[AgentRun] = relationship("AgentRun", back_populates="steps")


__all__ = ["AgentRun", "AgentRunStep"]
