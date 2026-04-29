"""F31 — Tables action_plan + action_step + RLS.

Revision ID: 0021_f31_action_plan
Revises: 0020_f30_attestations
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0021_f31_action_plan"
down_revision: str | None = "0020_f30_attestations"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ------------------------------------------------------------------
    # Enums Postgres
    # ------------------------------------------------------------------
    op.execute(
        """
        DO $$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'action_step_category') THEN
                CREATE TYPE action_step_category AS ENUM ('esg','carbone','credit','candidature');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'action_step_priority') THEN
                CREATE TYPE action_step_priority AS ENUM ('haute','moyenne','basse');
            END IF;
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'action_step_status') THEN
                CREATE TYPE action_step_status AS ENUM ('todo','doing','done','postponed');
            END IF;
        END$$;
        """
    )

    # ------------------------------------------------------------------
    # action_plan
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS action_plan (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
            horizon_months INTEGER NOT NULL,
            version INTEGER NOT NULL,
            score_calculation_id UUID NULL REFERENCES score_calculation(id) ON DELETE SET NULL,
            generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            generated_by_user_id UUID NULL REFERENCES account_user(id) ON DELETE SET NULL,
            CONSTRAINT chk_action_plan_horizon CHECK (horizon_months IN (6,12,24)),
            CONSTRAINT chk_action_plan_version CHECK (version >= 1),
            CONSTRAINT uq_action_plan_account_version UNIQUE (account_id, version)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_action_plan_account_generated
        ON action_plan(account_id, generated_at DESC)
        """
    )

    # ------------------------------------------------------------------
    # action_step
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS action_step (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            plan_id UUID NOT NULL REFERENCES action_plan(id) ON DELETE CASCADE,
            title TEXT NOT NULL,
            description TEXT NULL,
            category action_step_category NOT NULL,
            priority action_step_priority NOT NULL,
            horizon_at DATE NOT NULL,
            status action_step_status NOT NULL DEFAULT 'todo',
            responsible_user_id UUID NULL REFERENCES account_user(id) ON DELETE SET NULL,
            indicateur_id UUID NULL REFERENCES indicateur(id) ON DELETE SET NULL,
            source_id UUID NULL REFERENCES source(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_action_step_title_len CHECK (char_length(title) BETWEEN 3 AND 200)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_action_step_plan
        ON action_step(plan_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_action_step_plan_priority_horizon
        ON action_step(plan_id, priority, horizon_at)
        """
    )

    # ------------------------------------------------------------------
    # GRANTs (rôle applicatif)
    # ------------------------------------------------------------------
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON action_plan TO app_user")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON action_step TO app_user")
    op.execute("GRANT ALL ON action_plan TO migrator")
    op.execute("GRANT ALL ON action_step TO migrator")

    # ------------------------------------------------------------------
    # RLS — pattern F02 standard (admin bypass + account_id)
    # ------------------------------------------------------------------
    op.execute("ALTER TABLE action_plan ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE action_plan FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON action_plan")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON action_plan
        USING (
            COALESCE(NULLIF(current_setting('app.is_admin', true), ''), 'false')::bool IS TRUE
            OR account_id = NULLIF(current_setting('app.current_account_id', true), '')::uuid
        )
        WITH CHECK (
            COALESCE(NULLIF(current_setting('app.is_admin', true), ''), 'false')::bool IS TRUE
            OR account_id = NULLIF(current_setting('app.current_account_id', true), '')::uuid
        )
        """
    )

    op.execute("ALTER TABLE action_step ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE action_step FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON action_step")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON action_step
        USING (
            COALESCE(NULLIF(current_setting('app.is_admin', true), ''), 'false')::bool IS TRUE
            OR plan_id IN (
                SELECT id FROM action_plan
                 WHERE account_id = NULLIF(current_setting('app.current_account_id', true), '')::uuid
            )
        )
        WITH CHECK (
            COALESCE(NULLIF(current_setting('app.is_admin', true), ''), 'false')::bool IS TRUE
            OR plan_id IN (
                SELECT id FROM action_plan
                 WHERE account_id = NULLIF(current_setting('app.current_account_id', true), '')::uuid
            )
        )
        """
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS action_step CASCADE")
    op.execute("DROP TABLE IF EXISTS action_plan CASCADE")
    op.execute("DROP TYPE IF EXISTS action_step_status")
    op.execute("DROP TYPE IF EXISTS action_step_priority")
    op.execute("DROP TYPE IF EXISTS action_step_category")
