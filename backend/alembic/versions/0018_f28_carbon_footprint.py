"""F28 - Table carbon_footprint + RLS.

Revision ID: 0018_f28_carbon_footprint
Revises: 0017_f24_rapport_genere
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0018_f28_carbon_footprint"
down_revision: str | None = "0017_f24_rapport_genere"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS carbon_footprint (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID NOT NULL REFERENCES account(id),
          entreprise_id UUID NULL,
          year INTEGER NOT NULL,
          source_data_json JSONB NOT NULL DEFAULT '{}'::jsonb,
          total_tco2e NUMERIC(18,6) NOT NULL DEFAULT 0,
          by_scope_json JSONB NOT NULL DEFAULT '{}'::jsonb,
          breakdown_json JSONB NOT NULL DEFAULT '[]'::jsonb,
          factor_versions_json JSONB NOT NULL DEFAULT '[]'::jsonb,
          computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          version INTEGER NOT NULL DEFAULT 1,
          CONSTRAINT chk_carbon_year CHECK (year BETWEEN 2000 AND 2100)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_carbon_footprint_lookup
        ON carbon_footprint(account_id, year, computed_at DESC)
        """
    )

    op.execute("GRANT SELECT, INSERT ON carbon_footprint TO app_user")
    op.execute("GRANT ALL ON carbon_footprint TO migrator")

    op.execute("ALTER TABLE carbon_footprint ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE carbon_footprint FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON carbon_footprint")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON carbon_footprint
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


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS carbon_footprint CASCADE")
