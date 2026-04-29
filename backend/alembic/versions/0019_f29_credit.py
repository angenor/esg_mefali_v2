"""F29 - Tables credit_data et credit_score + RLS.

Revision ID: 0019_f29_credit
Revises: 0018_f28_carbon_footprint
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0019_f29_credit"
down_revision: str | None = "0018_f28_carbon_footprint"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS credit_data (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID NOT NULL REFERENCES account(id),
          entreprise_id UUID NOT NULL,
          kind VARCHAR(32) NOT NULL,
          payload_json JSONB NOT NULL,
          consent_id UUID NULL,
          uploaded_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          valid_until TIMESTAMPTZ NULL,
          CONSTRAINT chk_credit_data_kind CHECK (
            kind IN ('mobile_money','declaratif','photos','publique')
          )
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_credit_data_lookup
        ON credit_data(entreprise_id, kind, uploaded_at DESC)
        """
    )
    op.execute("GRANT SELECT, INSERT ON credit_data TO app_user")
    op.execute("GRANT ALL ON credit_data TO migrator")
    op.execute("ALTER TABLE credit_data ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE credit_data FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON credit_data")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON credit_data
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

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS credit_score (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID NOT NULL REFERENCES account(id),
          entreprise_id UUID NOT NULL,
          solvabilite SMALLINT NOT NULL,
          impact_vert SMALLINT NOT NULL,
          combine SMALLINT NOT NULL,
          facteurs JSONB NOT NULL DEFAULT '[]'::jsonb,
          methodologie_version INTEGER NOT NULL,
          coherence_warning BOOLEAN NOT NULL DEFAULT FALSE,
          computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT chk_credit_score_solvabilite CHECK (solvabilite BETWEEN 0 AND 100),
          CONSTRAINT chk_credit_score_impact CHECK (impact_vert BETWEEN 0 AND 100),
          CONSTRAINT chk_credit_score_combine CHECK (combine BETWEEN 0 AND 100)
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_credit_score_lookup
        ON credit_score(entreprise_id, computed_at DESC)
        """
    )
    op.execute("GRANT SELECT, INSERT ON credit_score TO app_user")
    op.execute("GRANT ALL ON credit_score TO migrator")
    op.execute("ALTER TABLE credit_score ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE credit_score FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON credit_score")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON credit_score
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
    op.execute("DROP TABLE IF EXISTS credit_score CASCADE")
    op.execute("DROP TABLE IF EXISTS credit_data CASCADE")
