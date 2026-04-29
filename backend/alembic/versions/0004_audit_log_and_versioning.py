"""F04 — Audit log append-only privileges + versioning EXCLUDE + snapshot trigger.

Revision ID: 0004_audit_log_and_versioning
Revises: 0003_source_anti_hallucination
Create Date: 2026-04-29

Builds on the F01 ``audit_log`` table:
- Adds ``request_id`` + ``ip`` columns.
- Converts ``source_of_change`` TEXT -> ENUM ``source_of_change_t`` (adds ``system``).
- Adds composite indexes per data-model.md §2.
- REVOKE UPDATE, DELETE, TRUNCATE on audit_log from app_user (append-only privilege gate).
- Enables RLS on audit_log with tenant_isolation USING + WITH CHECK on insert.

Versioning (T016..T019):
- For each of (referentiel, indicateur, critere, formule, seuil, facteur_emission, template):
  ADD COLUMN version (default 1), valid_from TIMESTAMPTZ, valid_to TIMESTAMPTZ NULL,
  parent_id UUID NULL self-FK, logical_id UUID NOT NULL.
  Backfill valid_from = COALESCE(created_at, now()), logical_id = gen_random_uuid()
  for existing rows.
- EXCLUDE USING gist on (logical_id WITH =, tstzrange(valid_from, valid_to) WITH &&)
  — requires btree_gist extension.
- Partial index <tbl>_logical_active_idx on (logical_id) WHERE valid_to IS NULL.

NOTE: ``formule`` and ``seuil`` are not present in F01 schema. They will be created
by F09 (catalogue référentiels). For F04, we make their alterations conditional
on table existence so the migration runs cleanly today and stays idempotent
when those tables are added later.

Snapshot immutability (T020..T021):
- ALTER candidature: snapshot_json column already exists (F01); add submitted_at
  if missing (F01 has soumission_at — alias).
- Trigger candidature_snapshot_immutable_trg: BEFORE UPDATE refuses changes to
  snapshot_json once submitted_at is set.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0004_audit_log_and_versioning"
down_revision: str | None = "0003_source_anti_hallucination"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Versioned catalogue tables. Order matters only for parent_id self-FK on
# referentiel (no cross-table FK in this migration).
VERSIONED_TABLES = (
    "referentiel",
    "indicateur",
    "critere",
    "formule",
    "seuil",
    "facteur_emission",
    "template",
)


def _table_exists(name: str) -> str:
    """Inline SQL guard."""
    return (
        "SELECT 1 FROM information_schema.tables "
        f"WHERE table_schema='public' AND table_name='{name}'"
    )


def upgrade() -> None:
    # 0) Extensions
    op.execute("CREATE EXTENSION IF NOT EXISTS btree_gist")

    # 1) ENUM source_of_change_t (closed list)
    op.execute(
        """
        DO $do$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname='source_of_change_t') THEN
                CREATE TYPE source_of_change_t AS ENUM
                    ('manual','llm','import','admin','system');
            END IF;
        END
        $do$;
        """
    )

    # 2) audit_log : add columns request_id + ip, convert source_of_change to enum.
    op.execute(
        "ALTER TABLE audit_log "
        "ADD COLUMN IF NOT EXISTS request_id TEXT NULL, "
        "ADD COLUMN IF NOT EXISTS ip INET NULL"
    )

    # Drop the old text CHECK then convert column type.
    op.execute("ALTER TABLE audit_log DROP CONSTRAINT IF EXISTS chk_audit_source")
    # Backfill any unknown values to 'manual' (defensive — F01 inserted only manual/admin).
    op.execute(
        "UPDATE audit_log SET source_of_change='manual' "
        "WHERE source_of_change NOT IN ('manual','llm','import','admin','system')"
    )
    op.execute(
        "ALTER TABLE audit_log "
        "ALTER COLUMN source_of_change TYPE source_of_change_t "
        "USING source_of_change::source_of_change_t"
    )

    # 3) Composite indexes
    op.execute(
        "CREATE INDEX IF NOT EXISTS audit_log_account_entity_ts_idx "
        'ON audit_log (account_id, entity_type, entity_id, "timestamp" DESC)'
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS audit_log_account_ts_idx "
        'ON audit_log (account_id, "timestamp" DESC)'
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS audit_log_admin_ts_idx "
        'ON audit_log ("timestamp" DESC) '
        "WHERE source_of_change IN ('admin','system')"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS audit_log_request_id_idx "
        "ON audit_log (request_id) WHERE request_id IS NOT NULL"
    )

    # 4) RLS on audit_log + privilege model.
    op.execute("ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE audit_log FORCE ROW LEVEL SECURITY")

    op.execute("DROP POLICY IF EXISTS audit_log_tenant_isolation ON audit_log")
    op.execute(
        """
        CREATE POLICY audit_log_tenant_isolation ON audit_log
        FOR SELECT
        USING (
            COALESCE(NULLIF(current_setting('app.is_admin', true), ''), 'false')::bool IS TRUE
            OR account_id IS NULL
            OR account_id = NULLIF(current_setting('app.current_account_id', true), '')::uuid
        );
        """
    )

    # INSERT policy : permissive — any authenticated session can append a row,
    # but only matching its account_id (or NULL for system events).
    op.execute("DROP POLICY IF EXISTS audit_log_insert_any ON audit_log")
    op.execute(
        """
        CREATE POLICY audit_log_insert_any ON audit_log
        FOR INSERT
        WITH CHECK (
            COALESCE(NULLIF(current_setting('app.is_admin', true), ''), 'false')::bool IS TRUE
            OR account_id IS NULL
            OR account_id = NULLIF(current_setting('app.current_account_id', true), '')::uuid
        );
        """
    )

    # Privilege gate (SC-002): app_user can SELECT / INSERT only.
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM app_user")
    op.execute("REVOKE UPDATE, DELETE, TRUNCATE ON audit_log FROM PUBLIC")
    op.execute("GRANT INSERT, SELECT ON audit_log TO app_user")
    # F01 used UUID PK (no sequence) — nothing to grant on a sequence.

    # 5) Versioning : ADD columns on each existing versioned table.
    # Special case: ``referentiel`` (F01) already exposes valid_from/valid_to
    # as DATE columns and ``version`` as TEXT. We migrate them in-place to the
    # F04 contract: TIMESTAMPTZ for ranges, INTEGER ``version_num`` alongside.
    op.execute(
        """
        DO $do$
        BEGIN
            IF EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='referentiel' AND column_name='valid_from'
                  AND data_type='date'
            ) THEN
                ALTER TABLE referentiel
                    ALTER COLUMN valid_from TYPE TIMESTAMPTZ
                    USING (valid_from::timestamptz),
                    ALTER COLUMN valid_to TYPE TIMESTAMPTZ
                    USING (valid_to::timestamptz);
            END IF;
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='referentiel' AND column_name='version_num'
            ) THEN
                ALTER TABLE referentiel
                    ADD COLUMN version_num INT NOT NULL DEFAULT 1;
            END IF;
        END
        $do$;
        """
    )

    for tbl in VERSIONED_TABLES:
        op.execute(
            f"""
            DO $do$
            BEGIN
                IF EXISTS ({_table_exists(tbl)}) THEN
                    ALTER TABLE {tbl}
                        ADD COLUMN IF NOT EXISTS valid_from TIMESTAMPTZ NULL,
                        ADD COLUMN IF NOT EXISTS valid_to   TIMESTAMPTZ NULL,
                        ADD COLUMN IF NOT EXISTS parent_id  UUID NULL,
                        ADD COLUMN IF NOT EXISTS logical_id UUID NULL,
                        ADD COLUMN IF NOT EXISTS version    INT NOT NULL DEFAULT 1;
                END IF;
            END
            $do$;
            """
        )

    # 6) Backfill existing rows.
    for tbl in VERSIONED_TABLES:
        op.execute(
            f"""
            DO $do$
            BEGIN
                IF EXISTS ({_table_exists(tbl)}) THEN
                    UPDATE {tbl}
                    SET valid_from = COALESCE(valid_from, created_at, now()),
                        logical_id = COALESCE(logical_id, gen_random_uuid())
                    WHERE valid_from IS NULL OR logical_id IS NULL;
                    -- Promote logical_id NOT NULL once backfilled, and add
                    -- a default so callers (and existing tests) need not
                    -- supply it explicitly.
                    ALTER TABLE {tbl} ALTER COLUMN logical_id SET DEFAULT gen_random_uuid();
                    ALTER TABLE {tbl} ALTER COLUMN logical_id SET NOT NULL;
                    ALTER TABLE {tbl} ALTER COLUMN valid_from SET NOT NULL;
                    ALTER TABLE {tbl} ALTER COLUMN valid_from SET DEFAULT now();
                END IF;
            END
            $do$;
            """
        )

    # 7) Self-FK parent_id (no ON DELETE CASCADE — preserve history).
    for tbl in VERSIONED_TABLES:
        op.execute(
            f"""
            DO $do$
            BEGIN
                IF EXISTS ({_table_exists(tbl)})
                   AND NOT EXISTS (
                     SELECT 1 FROM information_schema.table_constraints
                     WHERE table_name='{tbl}' AND constraint_name='fk_{tbl}_parent'
                   ) THEN
                    ALTER TABLE {tbl}
                      ADD CONSTRAINT fk_{tbl}_parent
                      FOREIGN KEY (parent_id) REFERENCES {tbl}(id);
                END IF;
            END
            $do$;
            """
        )

    # 8) EXCLUDE USING gist + partial active index.
    for tbl in VERSIONED_TABLES:
        op.execute(
            f"""
            DO $do$
            BEGIN
                IF EXISTS ({_table_exists(tbl)})
                   AND NOT EXISTS (
                     SELECT 1 FROM pg_constraint
                     WHERE conname='{tbl}_logical_no_overlap'
                   ) THEN
                    ALTER TABLE {tbl}
                      ADD CONSTRAINT {tbl}_logical_no_overlap
                      EXCLUDE USING gist (
                        logical_id WITH =,
                        tstzrange(valid_from, valid_to) WITH &&
                      );
                END IF;
            END
            $do$;
            """
        )
        op.execute(
            f"""
            DO $do$
            BEGIN
                IF EXISTS ({_table_exists(tbl)}) THEN
                    CREATE INDEX IF NOT EXISTS {tbl}_logical_active_idx
                      ON {tbl} (logical_id) WHERE valid_to IS NULL;
                END IF;
            END
            $do$;
            """
        )

    # 9) Candidature snapshot guard.
    # F01 created columns: snapshot_json JSONB NULL, soumission_at TIMESTAMP NULL.
    # We add submitted_at (alias) only if absent and rely on it for the trigger.
    op.execute(
        """
        DO $do$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='candidature' AND column_name='submitted_at'
            ) THEN
                ALTER TABLE candidature
                  ADD COLUMN submitted_at TIMESTAMPTZ NULL;
                -- One-shot copy from soumission_at (legacy column name).
                UPDATE candidature SET submitted_at = soumission_at
                WHERE soumission_at IS NOT NULL AND submitted_at IS NULL;
            END IF;
        END
        $do$;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION candidature_snapshot_guard()
        RETURNS trigger AS $body$
        BEGIN
            -- Once a candidature is submitted (snapshot_json + submitted_at set),
            -- snapshot_json and submitted_at must be immutable (SC-008).
            IF OLD.snapshot_json IS NOT NULL AND OLD.submitted_at IS NOT NULL THEN
                IF NEW.snapshot_json IS DISTINCT FROM OLD.snapshot_json THEN
                    RAISE EXCEPTION
                        'snapshot_json is immutable after submission (candidature.id=%)',
                        OLD.id
                        USING ERRCODE = 'check_violation';
                END IF;
                IF NEW.submitted_at IS DISTINCT FROM OLD.submitted_at THEN
                    RAISE EXCEPTION
                        'submitted_at is immutable after submission (candidature.id=%)',
                        OLD.id
                        USING ERRCODE = 'check_violation';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $body$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS candidature_snapshot_immutable_trg ON candidature")
    op.execute(
        """
        CREATE TRIGGER candidature_snapshot_immutable_trg
        BEFORE UPDATE ON candidature
        FOR EACH ROW EXECUTE FUNCTION candidature_snapshot_guard();
        """
    )


def downgrade() -> None:
    # 9) Candidature snapshot guard
    op.execute("DROP TRIGGER IF EXISTS candidature_snapshot_immutable_trg ON candidature")
    op.execute("DROP FUNCTION IF EXISTS candidature_snapshot_guard()")
    op.execute("ALTER TABLE candidature DROP COLUMN IF EXISTS submitted_at")

    # 8) EXCLUDE + partial index
    for tbl in VERSIONED_TABLES:
        op.execute(f"DROP INDEX IF EXISTS {tbl}_logical_active_idx")
        op.execute(
            f"ALTER TABLE IF EXISTS {tbl} "
            f"DROP CONSTRAINT IF EXISTS {tbl}_logical_no_overlap"
        )

    # 7) FK parent_id
    for tbl in VERSIONED_TABLES:
        op.execute(
            f"ALTER TABLE IF EXISTS {tbl} "
            f"DROP CONSTRAINT IF EXISTS fk_{tbl}_parent"
        )

    # 5/6) Drop columns
    for tbl in VERSIONED_TABLES:
        op.execute(
            f"ALTER TABLE IF EXISTS {tbl} "
            "DROP COLUMN IF EXISTS logical_id, "
            "DROP COLUMN IF EXISTS parent_id, "
            "DROP COLUMN IF EXISTS valid_to, "
            "DROP COLUMN IF EXISTS valid_from"
        )
    op.execute("ALTER TABLE IF EXISTS referentiel DROP COLUMN IF EXISTS version_num")

    # 4) RLS + privileges
    op.execute("DROP POLICY IF EXISTS audit_log_insert_any ON audit_log")
    op.execute("DROP POLICY IF EXISTS audit_log_tenant_isolation ON audit_log")
    op.execute("ALTER TABLE audit_log DISABLE ROW LEVEL SECURITY")
    # Restore broad privileges (legacy state).
    op.execute("GRANT UPDATE, DELETE ON audit_log TO app_user")

    # 3) Indexes
    op.execute("DROP INDEX IF EXISTS audit_log_request_id_idx")
    op.execute("DROP INDEX IF EXISTS audit_log_admin_ts_idx")
    op.execute("DROP INDEX IF EXISTS audit_log_account_ts_idx")
    op.execute("DROP INDEX IF EXISTS audit_log_account_entity_ts_idx")

    # 2) Convert source_of_change back to TEXT and re-add CHECK
    op.execute(
        "ALTER TABLE audit_log ALTER COLUMN source_of_change TYPE TEXT "
        "USING source_of_change::text"
    )
    op.execute(
        "ALTER TABLE audit_log "
        "ADD CONSTRAINT chk_audit_source "
        "CHECK (source_of_change IN ('manual','llm','import','admin'))"
    )
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS ip")
    op.execute("ALTER TABLE audit_log DROP COLUMN IF EXISTS request_id")

    # 1) Type enum (only if not used elsewhere)
    op.execute("DROP TYPE IF EXISTS source_of_change_t")
