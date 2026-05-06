"""F56 — unsourced_flag table + agent_run.sourcing_status + chat_message.sources.

Adds the structural enforcement for constitutional invariant P1 :
1. ``unsourced_flag`` : new RLS-scoped table tracking factual claims that the
   LLM cannot source. INSERT-only on ``app_user`` ; admin role updates
   ``resolved_at``/``resolved_by``. Partial UNIQUE index for dedup
   ``(account_id, thread_id, lower(claim)) WHERE resolved_at IS NULL``.
2. ``agent_run.sourcing_status`` : ``ok|retried_ok|failed|null`` ; populated
   by the validator (FR-009/FR-010).
3. ``chat_message.sources`` : ``JSONB NULL`` ; aggregated SourceRef list
   citing the message + GIN index for top-source queries (FR-013).
4. Conditional ``source.embedding`` cosine index (HNSW with ivfflat fallback)
   if F03 didn't already create one.

All operations are idempotent (``IF NOT EXISTS`` / ``IF EXISTS``) and
reversible. No data migration.

Revision ID: 0035_f56_unsourced_flag_and_sourcing_columns
Revises: 0034_f55_audit_tool_call_extensions
Create Date: 2026-05-06
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0035_f56_unsourced_flag_and_sourcing_columns"
down_revision: str | None = "0034_f55_audit_tool_call_extensions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply F56 schema additions.

    Order:
    1. ``unsourced_flag`` table + indexes + RLS + permissions.
    2. ``agent_run.sourcing_status`` column.
    3. ``chat_message.sources`` JSONB column + GIN index.
    4. Conditional ``source.embedding`` cosine index.
    """

    # ------------------------------------------------------------------
    # 1. unsourced_flag table
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS unsourced_flag (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES account_user(id),
            agent_run_id UUID NULL REFERENCES agent_run(id) ON DELETE SET NULL,
            thread_id UUID NULL,
            message_id UUID NULL,
            claim TEXT NOT NULL CHECK (length(claim) BETWEEN 1 AND 1000),
            reason TEXT NOT NULL CHECK (length(reason) BETWEEN 1 AND 500),
            source_of_change source_of_change_t NOT NULL DEFAULT 'llm',
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            resolved_at TIMESTAMPTZ NULL,
            resolved_by UUID NULL REFERENCES account_user(id),
            version BIGINT NOT NULL DEFAULT 1
        )
        """
    )

    # Indexes
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_unsourced_flag_account_created
            ON unsourced_flag (account_id, created_at DESC)
        """
    )
    # Dedup partial UNIQUE (Q1 clarification)
    # NULLS NOT DISTINCT (PG 15+) garantit que deux rows avec
    # ``thread_id=NULL`` et le même claim normalisé sont considérées comme
    # dupliquées par l'index. Fallback : COALESCE pour PG < 15.
    op.execute(
        """
        DO $$
        DECLARE
            pg_major int;
        BEGIN
            SELECT current_setting('server_version_num')::int / 10000 INTO pg_major;
            IF pg_major >= 15 THEN
                EXECUTE 'CREATE UNIQUE INDEX IF NOT EXISTS '
                     || 'ix_unsourced_flag_unique_unresolved '
                     || 'ON unsourced_flag (account_id, thread_id, lower(claim)) '
                     || 'NULLS NOT DISTINCT '
                     || 'WHERE resolved_at IS NULL';
            ELSE
                EXECUTE 'CREATE UNIQUE INDEX IF NOT EXISTS '
                     || 'ix_unsourced_flag_unique_unresolved '
                     || 'ON unsourced_flag (account_id, '
                     || 'COALESCE(thread_id, '
                     || quote_literal('00000000-0000-0000-0000-000000000000') || '::uuid), '
                     || 'lower(claim)) '
                     || 'WHERE resolved_at IS NULL';
            END IF;
        END
        $$;
        """
    )
    # Admin backlog filtering
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_unsourced_flag_unresolved
            ON unsourced_flag (account_id, created_at DESC)
            WHERE resolved_at IS NULL
        """
    )

    # RLS (P2)
    op.execute("ALTER TABLE unsourced_flag ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE unsourced_flag FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'unsourced_flag'
                  AND policyname = 'unsourced_flag_account_isolation'
            ) THEN
                EXECUTE 'CREATE POLICY unsourced_flag_account_isolation '
                     || 'ON unsourced_flag '
                     || 'USING (account_id = current_setting('
                     || quote_literal('app.current_account_id') || ', true)::uuid) '
                     || 'WITH CHECK (account_id = current_setting('
                     || quote_literal('app.current_account_id') || ', true)::uuid)';
            END IF;
        END
        $$;
        """
    )

    # Permissions (P3 audit append-only) :
    # - app_user : SELECT, INSERT (no UPDATE / DELETE — append-only).
    # - app_admin : UPDATE on resolved_* columns only.
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
                EXECUTE 'GRANT SELECT, INSERT ON unsourced_flag TO app_user';
                EXECUTE 'REVOKE UPDATE, DELETE ON unsourced_flag FROM app_user';
            END IF;
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_admin') THEN
                EXECUTE 'GRANT SELECT, INSERT ON unsourced_flag TO app_admin';
                EXECUTE 'GRANT UPDATE (resolved_at, resolved_by, version) '
                     || 'ON unsourced_flag TO app_admin';
            END IF;
        END
        $$;
        """
    )

    # ------------------------------------------------------------------
    # 2. agent_run.sourcing_status
    # ------------------------------------------------------------------
    op.execute(
        """
        ALTER TABLE agent_run
            ADD COLUMN IF NOT EXISTS sourcing_status TEXT NULL
        """
    )
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.constraint_column_usage
                WHERE table_name = 'agent_run'
                  AND constraint_name = 'chk_agent_run_sourcing_status'
            ) THEN
                EXECUTE 'ALTER TABLE agent_run '
                     || 'ADD CONSTRAINT chk_agent_run_sourcing_status '
                     || 'CHECK (sourcing_status IS NULL OR '
                     || 'sourcing_status IN ('
                     || quote_literal('ok') || ','
                     || quote_literal('retried_ok') || ','
                     || quote_literal('failed') || '))';
            END IF;
        END
        $$;
        """
    )

    # ------------------------------------------------------------------
    # 3. chat_message.sources JSONB + GIN index (FR-018)
    # ------------------------------------------------------------------
    op.execute(
        """
        ALTER TABLE chat_message
            ADD COLUMN IF NOT EXISTS sources JSONB NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_chat_message_sources_gin
            ON chat_message USING GIN (sources)
        """
    )

    # ------------------------------------------------------------------
    # 4. Conditional source.embedding cosine index (HNSW preferred, ivfflat fallback)
    # ------------------------------------------------------------------
    # HNSW first ; on failure (pgvector < 0.5) fall back to ivfflat.
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'source'
                  AND indexname IN (
                      'ix_source_embedding_cosine',
                      'ix_source_embedding_cosine_ivfflat',
                      'source_embedding_idx'
                  )
            ) THEN
                BEGIN
                    EXECUTE 'CREATE INDEX ix_source_embedding_cosine '
                         || 'ON source USING hnsw (embedding vector_cosine_ops)';
                EXCEPTION WHEN feature_not_supported THEN
                    EXECUTE 'CREATE INDEX ix_source_embedding_cosine_ivfflat '
                         || 'ON source USING ivfflat (embedding vector_cosine_ops) '
                         || 'WITH (lists = 100)';
                WHEN undefined_object THEN
                    EXECUTE 'CREATE INDEX ix_source_embedding_cosine_ivfflat '
                         || 'ON source USING ivfflat (embedding vector_cosine_ops) '
                         || 'WITH (lists = 100)';
                END;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Reverse all F56 schema additions (idempotent)."""
    op.execute("DROP INDEX IF EXISTS ix_source_embedding_cosine")
    op.execute("DROP INDEX IF EXISTS ix_source_embedding_cosine_ivfflat")
    op.execute("DROP INDEX IF EXISTS ix_chat_message_sources_gin")
    op.execute("ALTER TABLE chat_message DROP COLUMN IF EXISTS sources")
    op.execute(
        "ALTER TABLE agent_run DROP CONSTRAINT IF EXISTS chk_agent_run_sourcing_status"
    )
    op.execute("ALTER TABLE agent_run DROP COLUMN IF EXISTS sourcing_status")
    op.execute("DROP INDEX IF EXISTS ix_unsourced_flag_unresolved")
    op.execute("DROP INDEX IF EXISTS ix_unsourced_flag_unique_unresolved")
    op.execute("DROP INDEX IF EXISTS ix_unsourced_flag_account_created")
    op.execute("DROP TABLE IF EXISTS unsourced_flag CASCADE")
