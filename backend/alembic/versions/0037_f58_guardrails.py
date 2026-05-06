"""F58 — Agent guardrails (tool kill-switch + token quotas + run flags + step flow).

Revision ID: 0037
Revises: 0036
Create Date: 2026-05-06 00:00:00

Changes:
- New table ``agent_tool_status`` (kill-switch admin global).
- ALTER ``account``: 3 sub-quotas tokens (CHECK constraint).
- ALTER ``agent_run``: 6 guardrails flags + CHECK constraint on ``mode``.
- ALTER ``agent_run_step``: ``flow`` column (CHECK).
- 3 indexes for dashboard performance.

Notes:
- ``agent_tool_status`` is GLOBAL (no ``account_id``). Access gated by admin
  endpoint with ``require_admin``; non-admin gets 404 (P2 convention).
- All ALTER additions use safe defaults so the migration is non-destructive
  and applies immediately to existing rows.
"""
from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers
revision: str = "0037_f58_guardrails"
down_revision: str | None = "0036_f57_memory_rag"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # 1) Table agent_tool_status (no RLS — global admin-managed).
    op.create_table(
        "agent_tool_status",
        sa.Column("tool_name", sa.String(length=100), primary_key=True),
        sa.Column(
            "enabled",
            sa.Boolean,
            nullable=False,
            server_default=sa.true(),
        ),
        sa.Column(
            "disabled_at",
            sa.DateTime(timezone=True),
            nullable=True,
        ),
        sa.Column(
            "disabled_by",
            postgresql.UUID(as_uuid=True),
            nullable=True,
        ),
        sa.Column("reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.ForeignKeyConstraint(
            ["disabled_by"],
            ["account_user.id"],
            ondelete="SET NULL",
            name="fk_agent_tool_status_disabled_by_account_user",
        ),
    )

    # 2) Account: 3 sub-quotas
    op.add_column(
        "account",
        sa.Column(
            "daily_token_quota",
            sa.Integer,
            nullable=False,
            server_default="50000",
        ),
    )
    op.add_column(
        "account",
        sa.Column(
            "daily_conversation_quota",
            sa.Integer,
            nullable=False,
            server_default="30000",
        ),
    )
    op.add_column(
        "account",
        sa.Column(
            "daily_ocr_analysis_quota",
            sa.Integer,
            nullable=False,
            server_default="20000",
        ),
    )
    op.create_check_constraint(
        "ck_account_quota_sum",
        "account",
        "daily_conversation_quota + daily_ocr_analysis_quota <= daily_token_quota",
    )

    # 3) agent_run: 6 guardrails flags + mode CHECK
    op.add_column(
        "agent_run",
        sa.Column(
            "injection_detected",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "agent_run",
        sa.Column(
            "pii_masked_count",
            sa.Integer,
            nullable=False,
            server_default="0",
        ),
    )
    op.add_column(
        "agent_run",
        sa.Column(
            "language_corrected",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "agent_run",
        sa.Column(
            "loop_detected",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "agent_run",
        sa.Column(
            "circuit_breaker_open",
            sa.Boolean,
            nullable=False,
            server_default=sa.false(),
        ),
    )
    op.add_column(
        "agent_run",
        sa.Column(
            "mode",
            sa.String(length=20),
            nullable=False,
            server_default="langgraph",
        ),
    )
    op.create_check_constraint(
        "ck_agent_run_mode",
        "agent_run",
        "mode IN ('langgraph', 'raw', 'minimal')",
    )
    op.create_index(
        "idx_agent_run_metrics",
        "agent_run",
        ["account_id", "started_at", "injection_detected"],
    )
    op.create_index(
        "idx_agent_run_mode",
        "agent_run",
        ["mode", "started_at"],
    )

    # 4) agent_run_step: flow column
    op.add_column(
        "agent_run_step",
        sa.Column(
            "flow",
            sa.String(length=20),
            nullable=False,
            server_default="conversation",
        ),
    )
    op.create_check_constraint(
        "ck_agent_run_step_flow",
        "agent_run_step",
        "flow IN ('conversation', 'ocr_analysis')",
    )
    op.create_index(
        "idx_agent_run_step_token_acct",
        "agent_run_step",
        ["account_id", "started_at", "flow"],
    )

    # 5) Grants — table agent_tool_status est globale (admin uniquement) mais
    # le SELECT doit être ouvert à app_user pour que get_disabled_tools puisse
    # filtrer les tools côté node ; INSERT/UPDATE/DELETE restent accessibles
    # à app_user car les endpoints admin sont gated par require_admin (l'app
    # n'utilise pas un rôle DB séparé pour les admin en MVP).
    op.execute(
        "GRANT SELECT, INSERT, UPDATE, DELETE ON agent_tool_status TO app_user"
    )
    op.execute("GRANT ALL ON agent_tool_status TO migrator")


def downgrade() -> None:
    op.drop_index("idx_agent_run_step_token_acct", table_name="agent_run_step")
    op.drop_constraint("ck_agent_run_step_flow", "agent_run_step")
    op.drop_column("agent_run_step", "flow")

    op.drop_index("idx_agent_run_mode", table_name="agent_run")
    op.drop_index("idx_agent_run_metrics", table_name="agent_run")
    op.drop_constraint("ck_agent_run_mode", "agent_run")
    for col in (
        "mode",
        "circuit_breaker_open",
        "loop_detected",
        "language_corrected",
        "pii_masked_count",
        "injection_detected",
    ):
        op.drop_column("agent_run", col)

    op.drop_constraint("ck_account_quota_sum", "account")
    for col in (
        "daily_ocr_analysis_quota",
        "daily_conversation_quota",
        "daily_token_quota",
    ):
        op.drop_column("account", col)

    op.drop_table("agent_tool_status")
