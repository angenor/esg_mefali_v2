"""F57 — Agent Memory & Long-term Recall (RAG, compaction, entity memory).

Adds the structural pieces needed for the constitutional invariants P2/P3
on the agent memory layer :

1. ``chat_thread.summary`` (TEXT NULL) and ``chat_thread.last_compacted_at``
   (TIMESTAMPTZ NULL) for the async compaction (US6).
2. ``chat_message.compacted`` (BOOL NOT NULL DEFAULT FALSE) — flags a
   message included in a summary, excluded from future recall (kept for
   audit P3).
3. ``agent_entity_memory`` (NEW) — account-wide stable facts per business
   entity (US7) with RLS policy + UNIQUE (account_id, entity_type, entity_id).
4. ``recall_log`` (NEW) — append-only tracing of recall operations (US9)
   with RLS policy + REVOKE UPDATE/DELETE on app_user (P3).
5. Add the ``memory_system`` value to the ``source_of_change_t`` enum so
   that audit_log writes from compaction / entity_memory CRUD / forget
   RGPD (FR-019) stay typed.
6. ``chat_message_embedding_hnsw_idx`` (HNSW with ivfflat fallback for
   pgvector < 0.5 — coexists with the existing ivfflat index from F18).

All operations idempotent (``IF NOT EXISTS`` / ``IF EXISTS``) and
reversible. No data migration.

Revision ID: 0036_f57_memory_rag
Revises: 0035_f56_unsourced_flag_and_sourcing_columns
Create Date: 2026-05-06
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0036_f57_memory_rag"
down_revision: str | None = "0035_f56_unsourced_flag_and_sourcing_columns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply F57 schema additions.

    Order matters :
    1. extend ``source_of_change_t`` enum (must be in its own transaction
       block but Alembic wraps in BEGIN — we use ALTER TYPE ADD VALUE IF
       NOT EXISTS which is supported since PG 12).
    2. chat_thread.summary + last_compacted_at columns.
    3. chat_message.compacted column.
    4. agent_entity_memory table + indexes + RLS + permissions.
    5. recall_log table + indexes + RLS + REVOKE UPDATE/DELETE.
    6. HNSW index attempt (best-effort).
    """

    # ------------------------------------------------------------------
    # 1. Extend enum source_of_change_t (FR-019)
    # ------------------------------------------------------------------
    # ALTER TYPE ... ADD VALUE IF NOT EXISTS requires PG 12+ and must run
    # outside of a transaction in older versions. PG 14+ allows it inside.
    op.execute(
        "ALTER TYPE source_of_change_t ADD VALUE IF NOT EXISTS 'memory_system'"
    )

    # ------------------------------------------------------------------
    # 2. chat_thread extensions (FR-005)
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TABLE chat_thread ADD COLUMN IF NOT EXISTS summary TEXT NULL"
    )
    op.execute(
        "ALTER TABLE chat_thread "
        "ADD COLUMN IF NOT EXISTS last_compacted_at TIMESTAMPTZ NULL"
    )

    # ------------------------------------------------------------------
    # 3. chat_message extension (FR-005)
    # ------------------------------------------------------------------
    op.execute(
        "ALTER TABLE chat_message "
        "ADD COLUMN IF NOT EXISTS compacted BOOLEAN NOT NULL DEFAULT FALSE"
    )

    # ------------------------------------------------------------------
    # 4. agent_entity_memory (FR-009, US7)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS agent_entity_memory (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
            entity_type TEXT NOT NULL CHECK (entity_type IN
                ('Entreprise','Projet','Candidature','Indicateur')),
            entity_id UUID NOT NULL,
            summary TEXT NOT NULL,
            sources_used JSONB NOT NULL DEFAULT '[]'::jsonb,
            last_updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            version INTEGER NOT NULL DEFAULT 1,
            CONSTRAINT uq_agent_entity_memory_account_entity
                UNIQUE (account_id, entity_type, entity_id)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_agent_entity_memory_account_entity
            ON agent_entity_memory (account_id, entity_type, entity_id)
        """
    )
    # RLS (P2)
    op.execute("ALTER TABLE agent_entity_memory ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE agent_entity_memory FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'agent_entity_memory'
                  AND policyname = 'agent_entity_memory_isolation'
            ) THEN
                EXECUTE 'CREATE POLICY agent_entity_memory_isolation '
                     || 'ON agent_entity_memory '
                     || 'USING (account_id = current_setting('
                     || quote_literal('app.current_account_id') || ', true)::uuid) '
                     || 'WITH CHECK (account_id = current_setting('
                     || quote_literal('app.current_account_id') || ', true)::uuid)';
            END IF;
        END
        $$;
        """
    )
    # Permissions (memory CRUD allowed for app_user — UPSERT + delete on entity removal)
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
                EXECUTE 'GRANT SELECT, INSERT, UPDATE, DELETE '
                     || 'ON agent_entity_memory TO app_user';
            END IF;
        END
        $$;
        """
    )

    # ------------------------------------------------------------------
    # 5. recall_log (FR-012, US9)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS recall_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            agent_run_id UUID NULL REFERENCES agent_run(id) ON DELETE SET NULL,
            account_id UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
            thread_id UUID NOT NULL REFERENCES chat_thread(id) ON DELETE CASCADE,
            recall_type TEXT NOT NULL
                CHECK (recall_type IN ('auto','tool')),
            query_hash TEXT NOT NULL,
            top_k INTEGER NOT NULL CHECK (top_k >= 0),
            top_scores JSONB NOT NULL,
            latency_ms INTEGER NOT NULL CHECK (latency_ms >= 0),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recall_log_account_run
            ON recall_log (account_id, agent_run_id)
            WHERE agent_run_id IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_recall_log_account_thread_time
            ON recall_log (account_id, thread_id, created_at DESC)
        """
    )
    op.execute("ALTER TABLE recall_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE recall_log FORCE ROW LEVEL SECURITY")
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_policies
                WHERE schemaname = 'public'
                  AND tablename = 'recall_log'
                  AND policyname = 'recall_log_isolation'
            ) THEN
                EXECUTE 'CREATE POLICY recall_log_isolation '
                     || 'ON recall_log '
                     || 'USING (account_id = current_setting('
                     || quote_literal('app.current_account_id') || ', true)::uuid) '
                     || 'WITH CHECK (account_id = current_setting('
                     || quote_literal('app.current_account_id') || ', true)::uuid)';
            END IF;
        END
        $$;
        """
    )
    # Append-only (P3) : SELECT + INSERT only on app_user, no UPDATE/DELETE
    op.execute(
        """
        DO $$
        BEGIN
            IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'app_user') THEN
                EXECUTE 'GRANT SELECT, INSERT ON recall_log TO app_user';
                EXECUTE 'REVOKE UPDATE, DELETE ON recall_log FROM app_user';
            END IF;
        END
        $$;
        """
    )

    # ------------------------------------------------------------------
    # 6. HNSW index on chat_message.embedding (best-effort) — coexists
    #    with the existing ivfflat index from F18 (idx_chat_message_embedding).
    # ------------------------------------------------------------------
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_indexes
                WHERE tablename = 'chat_message'
                  AND indexname = 'chat_message_embedding_hnsw_idx'
            ) THEN
                BEGIN
                    EXECUTE 'CREATE INDEX chat_message_embedding_hnsw_idx '
                         || 'ON chat_message USING hnsw (embedding vector_cosine_ops) '
                         || 'WITH (m = 16, ef_construction = 64)';
                EXCEPTION WHEN feature_not_supported THEN
                    -- pgvector < 0.5 : ivfflat already exists from F18, skip
                    NULL;
                WHEN undefined_object THEN
                    NULL;
                WHEN others THEN
                    -- swallow other index creation errors (best-effort)
                    NULL;
                END;
            END IF;
        END
        $$;
        """
    )


def downgrade() -> None:
    """Reverse F57 schema additions (idempotent)."""
    # Drop HNSW first
    op.execute("DROP INDEX IF EXISTS chat_message_embedding_hnsw_idx")

    # Drop new tables (CASCADE removes dependent indexes/policies)
    op.execute("DROP TABLE IF EXISTS recall_log CASCADE")
    op.execute("DROP TABLE IF EXISTS agent_entity_memory CASCADE")

    # Drop chat_message.compacted
    op.execute("ALTER TABLE chat_message DROP COLUMN IF EXISTS compacted")

    # Drop chat_thread additions
    op.execute("ALTER TABLE chat_thread DROP COLUMN IF EXISTS last_compacted_at")
    op.execute("ALTER TABLE chat_thread DROP COLUMN IF EXISTS summary")

    # NOTE: Postgres does not allow removing values from an enum, so the
    # 'memory_system' value remains present after downgrade. This is
    # harmless (value just becomes unused).
