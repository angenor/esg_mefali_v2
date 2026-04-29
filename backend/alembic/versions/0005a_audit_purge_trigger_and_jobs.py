"""F05 — Audit log purge-context trigger + scheduled_job_run table.

Revision ID: 0005a_audit_purge_trigger_and_jobs
Revises: 0004_audit_log_and_versioning
Create Date: 2026-04-29

Combines T007 (audit_log_immutable trigger with purge context exception)
and T008 (scheduled_job_run table for idempotent jobs).

Module 0 invariant: audit_log is append-only EXCEPT during a strict
``SET LOCAL app.purge_context='on'`` window where ONLY ``user_id`` may be
updated (RTBF pseudonymization). Any other UPDATE / DELETE is rejected.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005a_audit_purge_jobs"
down_revision: str | None = "0004_audit_log_and_versioning"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1) audit_log_immutable() — trigger function with RTBF exception.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION audit_log_immutable() RETURNS trigger AS $$
        BEGIN
          IF TG_OP = 'DELETE' THEN
            RAISE EXCEPTION 'audit_log is append-only';
          END IF;
          IF TG_OP = 'UPDATE' THEN
            IF current_setting('app.purge_context', true) IS DISTINCT FROM 'on' THEN
              RAISE EXCEPTION 'audit_log is append-only';
            END IF;
            IF NEW.account_id IS DISTINCT FROM OLD.account_id
               OR NEW."timestamp" IS DISTINCT FROM OLD."timestamp"
               OR NEW.entity_type IS DISTINCT FROM OLD.entity_type
               OR NEW.entity_id IS DISTINCT FROM OLD.entity_id
               OR NEW.field IS DISTINCT FROM OLD.field
               OR NEW.old_value IS DISTINCT FROM OLD.old_value
               OR NEW.new_value IS DISTINCT FROM OLD.new_value
               OR NEW.source_of_change IS DISTINCT FROM OLD.source_of_change THEN
              RAISE EXCEPTION 'audit_log purge context: only user_id may be updated';
            END IF;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS audit_log_immutable_trg ON audit_log")
    op.execute(
        """
        CREATE TRIGGER audit_log_immutable_trg
        BEFORE UPDATE OR DELETE ON audit_log
        FOR EACH ROW EXECUTE FUNCTION audit_log_immutable();
        """
    )

    # Privilege: re-allow UPDATE on user_id ONLY for migrator/app_user.
    # The trigger enforces the column-level rule; we still need GRANT UPDATE
    # to permit the operation to be attempted under purge_context.
    op.execute("GRANT UPDATE (user_id) ON audit_log TO app_user")

    # 2) scheduled_job_run table.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS scheduled_job_run (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            job_name TEXT NOT NULL CHECK (job_name IN
                ('purge_pending_deletions','refresh_fx_rates','alert_stale_fx')),
            run_date DATE NOT NULL,
            status TEXT NOT NULL CHECK (status IN ('running','success','failed')),
            message TEXT NULL,
            started_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            finished_at TIMESTAMPTZ NULL,
            UNIQUE (job_name, run_date)
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS scheduled_job_run_name_date_idx "
        "ON scheduled_job_run (job_name, run_date DESC)"
    )

    # RLS DISABLE on a table that is not tenant-scoped, but only migrator/admin
    # should write. We grant explicit privileges to app_user (read-only) and
    # rely on application code to use the migrator engine for inserts/updates.
    op.execute("ALTER TABLE scheduled_job_run DISABLE ROW LEVEL SECURITY")
    op.execute("REVOKE ALL ON scheduled_job_run FROM PUBLIC")
    op.execute("GRANT SELECT ON scheduled_job_run TO app_user")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS scheduled_job_run")
    op.execute("DROP TRIGGER IF EXISTS audit_log_immutable_trg ON audit_log")
    op.execute("DROP FUNCTION IF EXISTS audit_log_immutable()")
    op.execute("REVOKE UPDATE (user_id) ON audit_log FROM app_user")
