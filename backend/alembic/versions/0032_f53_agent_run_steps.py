"""F53 — agent_run + agent_run_step (append-only).

Crée :
- enums ``agent_run_status``, ``agent_step_status`` ;
- tables ``agent_run`` et ``agent_run_step`` (RLS-tenant, append-only) ;
- policies RLS ``account_isolation`` (cf. data-model section 2 et 3) ;
- REVOKE UPDATE/DELETE pour ``app_user`` (le runner utilise ``SET LOCAL ROLE
  app_admin`` pour l'unique UPDATE de complétion final).

Voir :file:`specs/053-agent-langgraph-core/data-model.md`.

Revision ID: 0032_f53_agent_run_steps
Revises: 0031_f52_notif_prefs_deletion_extension_exports
Create Date: 2026-05-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0032_f53_agent_run_steps"
down_revision: str | None = "0031_f52_notif_prefs_deletion_extension_exports"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


_RUN_STATUS = ("ok", "error", "timeout", "cancelled")
_STEP_STATUS = ("ok", "error", "timeout", "cancelled", "skipped")


def upgrade() -> None:
    """Crée les tables agent_run + agent_run_step + RLS + REVOKE."""
    # ------------------------------------------------------------------
    # 1. ENUMs
    # ------------------------------------------------------------------
    op.execute(
        "CREATE TYPE agent_run_status AS ENUM "
        f"({', '.join(repr(v) for v in _RUN_STATUS)})"
    )
    op.execute(
        "CREATE TYPE agent_step_status AS ENUM "
        f"({', '.join(repr(v) for v in _STEP_STATUS)})"
    )

    # ------------------------------------------------------------------
    # 2. agent_run (un row par tour de chat)
    # ------------------------------------------------------------------
    op.create_table(
        "agent_run",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("account.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("account_user.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("thread_id", sa.String(length=128), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(*_RUN_STATUS, name="agent_run_status", create_type=False),
            nullable=False,
            server_default="ok",
        ),
        sa.Column("total_latency_ms", sa.Integer(), nullable=True),
        sa.Column("total_tokens_in", sa.Integer(), nullable=True),
        sa.Column("total_tokens_out", sa.Integer(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("final_node", sa.String(length=64), nullable=True),
        sa.Column("error_summary", sa.Text(), nullable=True),
        sa.CheckConstraint(
            r"thread_id ~ '^[0-9a-f-]{36}:[0-9a-f-]{36}$'",
            name="agent_run_thread_id_format",
        ),
    )
    op.execute(
        "CREATE INDEX idx_agent_run_account_thread "
        "ON agent_run(account_id, thread_id, started_at DESC)"
    )
    op.execute(
        "CREATE INDEX idx_agent_run_status_started "
        "ON agent_run(status, started_at DESC) "
        "WHERE status != 'ok'"
    )

    # ------------------------------------------------------------------
    # 3. agent_run_step (un row par exécution de nœud)
    # ------------------------------------------------------------------
    op.create_table(
        "agent_run_step",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "run_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("agent_run.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "account_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("account.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("node_name", sa.String(length=64), nullable=False),
        sa.Column(
            "started_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("now()"),
        ),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("tokens_in", sa.Integer(), nullable=True),
        sa.Column("tokens_out", sa.Integer(), nullable=True),
        sa.Column(
            "tool_calls_count",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
        sa.Column(
            "status",
            postgresql.ENUM(
                *_STEP_STATUS, name="agent_step_status", create_type=False
            ),
            nullable=False,
            server_default="ok",
        ),
        sa.Column("error", sa.Text(), nullable=True),
    )
    op.execute(
        "CREATE INDEX idx_agent_run_step_run "
        "ON agent_run_step(run_id, started_at)"
    )
    op.execute(
        "CREATE INDEX idx_agent_run_step_account_node "
        "ON agent_run_step(account_id, node_name, started_at DESC)"
    )

    # ------------------------------------------------------------------
    # 4. RLS policies (gabarit account-isolation, P2)
    # ------------------------------------------------------------------
    for tbl in ("agent_run", "agent_run_step"):
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            DROP POLICY IF EXISTS {tbl}_account_isolation ON {tbl};
            CREATE POLICY {tbl}_account_isolation ON {tbl}
              USING (
                  account_id = current_setting('app.current_account_id', true)::uuid
                  OR current_setting('app.is_admin', true) = 'true'
              )
              WITH CHECK (
                  account_id = current_setting('app.current_account_id', true)::uuid
                  OR current_setting('app.is_admin', true) = 'true'
              );
            """
        )
        # app_user peut SELECT et INSERT mais NOT UPDATE/DELETE (P3 append-only).
        # Le runner promeut transitoirement vers app_admin pour l'unique UPDATE
        # de complétion (cf. data-model section 2).
        op.execute(f"GRANT SELECT, INSERT ON {tbl} TO app_user")
        op.execute(f"REVOKE UPDATE, DELETE ON {tbl} FROM app_user")
        op.execute(f"GRANT ALL ON {tbl} TO migrator")


def downgrade() -> None:
    """Révoque agent_run_step puis agent_run + ENUMs."""
    op.execute("DROP TABLE IF EXISTS agent_run_step CASCADE")
    op.execute("DROP TABLE IF EXISTS agent_run CASCADE")
    op.execute("DROP TYPE IF EXISTS agent_step_status")
    op.execute("DROP TYPE IF EXISTS agent_run_status")
