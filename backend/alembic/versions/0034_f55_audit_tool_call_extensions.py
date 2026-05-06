"""F55 — Tool call log + audit_log extensions for agent dispatch.

Cette migration livre :

- ``tool_call_log`` : nouvelle table tenant-scopée (P2 RLS) qui trace chaque
  tool call dispatché par l'agent (idempotency, status, dispatch_result_kind).
- ``audit_log`` : ajout de ``tool_call_id`` + ``agent_run_id`` (FK NULLABLE)
  pour la traçabilité totale des mutations LLM (FR-009, P3).

Aucune donnée existante n'est modifiée : pure addition idempotente.

Revision ID: 0034_f55_audit_tool_call_extensions
Revises: 0033_f54_alter_agent_run_prompt_hash
Create Date: 2026-05-06
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0034_f55_audit_tool_call_extensions"
down_revision: str | None = "0033_f54_alter_agent_run_prompt_hash"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée tool_call_log + ALTER audit_log + ALTER agent_run.metadata.

    1. tool_call_log : nouvelle table append-only (insert + update statut).
       RLS scoped, idempotency_key UNIQUE per (account_id, key).
    2. audit_log : tool_call_id + agent_run_id NULLABLE FK.
    3. agent_run : metadata JSONB NULLABLE pour pending_confirmations (US3).
    """

    # 0. agent_run.metadata (pour pending_confirmations US3)
    op.add_column(
        "agent_run",
        sa.Column(
            "metadata",
            sa.dialects.postgresql.JSONB(),
            nullable=True,
        ),
    )

    # 1. tool_call_log
    op.execute(
        """
        CREATE TABLE tool_call_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
            user_id UUID NULL REFERENCES account_user(id),
            agent_run_id UUID NULL REFERENCES agent_run(id) ON DELETE SET NULL,
            tool_call_id TEXT NOT NULL,
            tool_name TEXT NOT NULL,
            arguments_json JSONB NULL,
            status TEXT NOT NULL,
            dispatch_result_kind TEXT NULL,
            idempotency_key TEXT NULL,
            output_json JSONB NULL,
            error_summary TEXT NULL,
            entity_type TEXT NULL,
            entity_id UUID NULL,
            audit_log_id UUID NULL,
            duration_ms INTEGER NULL,
            is_dry_run BOOLEAN NOT NULL DEFAULT FALSE,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now(),
            version INT NOT NULL DEFAULT 1,
            CONSTRAINT chk_tool_call_status CHECK (status IN (
                'ok','error','skipped','rate_limited','cancelled_by_user',
                'confirmation_expired','pending_confirmation'
            )),
            CONSTRAINT chk_tool_call_dispatch_kind CHECK (
                dispatch_result_kind IS NULL OR
                dispatch_result_kind IN ('frontend_event','mutation_result','tool_message','error')
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX ix_tool_call_log_account_id ON tool_call_log(account_id)"
    )
    op.execute(
        "CREATE INDEX ix_tool_call_log_agent_run_id ON tool_call_log(agent_run_id) "
        "WHERE agent_run_id IS NOT NULL"
    )
    op.execute(
        "CREATE INDEX ix_tool_call_log_tool_name ON tool_call_log(tool_name)"
    )
    op.execute(
        "CREATE UNIQUE INDEX idx_tool_call_log_account_idempotency "
        "ON tool_call_log(account_id, idempotency_key) "
        "WHERE idempotency_key IS NOT NULL"
    )

    # RLS — tenant scoped
    op.execute("ALTER TABLE tool_call_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE tool_call_log FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        CREATE POLICY tool_call_log_tenant_isolation ON tool_call_log
        USING (account_id = current_setting('app.current_account_id')::uuid)
        WITH CHECK (account_id = current_setting('app.current_account_id')::uuid)
        """
    )

    # Permissions : app_user a INSERT + UPDATE (status finalisé après dispatch)
    # mais pas DELETE. app_admin role est conditionnel (peut ne pas exister
    # en environnement dev).
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
                EXECUTE 'GRANT SELECT, INSERT, UPDATE ON tool_call_log TO app_user';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_admin') THEN
                EXECUTE 'GRANT SELECT, INSERT, UPDATE ON tool_call_log TO app_admin';
            END IF;
        END
        $$;
        """
    )

    # 2. audit_log : tool_call_id + agent_run_id (FR-009)
    op.add_column(
        "audit_log",
        sa.Column("tool_call_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.add_column(
        "audit_log",
        sa.Column("agent_run_id", sa.dialects.postgresql.UUID(as_uuid=True), nullable=True),
    )
    op.execute(
        "ALTER TABLE audit_log "
        "ADD CONSTRAINT fk_audit_log_tool_call_id "
        "FOREIGN KEY (tool_call_id) REFERENCES tool_call_log(id) ON DELETE SET NULL"
    )
    op.execute(
        "ALTER TABLE audit_log "
        "ADD CONSTRAINT fk_audit_log_agent_run_id "
        "FOREIGN KEY (agent_run_id) REFERENCES agent_run(id) ON DELETE SET NULL"
    )
    op.execute(
        "CREATE INDEX idx_audit_log_tool_call_id "
        "ON audit_log(tool_call_id) WHERE tool_call_id IS NOT NULL"
    )


def downgrade() -> None:
    """Supprime extensions audit_log puis drop tool_call_log + agent_run.metadata."""
    op.execute("DROP INDEX IF EXISTS idx_audit_log_tool_call_id")
    op.execute(
        "ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS fk_audit_log_agent_run_id"
    )
    op.execute(
        "ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS fk_audit_log_tool_call_id"
    )
    op.drop_column("audit_log", "agent_run_id")
    op.drop_column("audit_log", "tool_call_id")

    op.execute("DROP TABLE IF EXISTS tool_call_log CASCADE")
    op.execute("ALTER TABLE agent_run DROP COLUMN IF EXISTS metadata")
