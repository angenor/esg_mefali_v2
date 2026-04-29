"""F23 — Table score_calculation (append-only) pour le scoring ESG MVP.

Cree :
- table score_calculation (account_id, entity_type, entity_id,
  referentiel_id/version/code, score_global, scores_by_pillar, details_json,
  coverage_ratio, computed_at/by).
- index lookup principal et partiel par referentiel.
- GRANTs app_user / migrator.
- RLS policy tenant_isolation (calque F12/F22).

Revision ID: 0016_f23_score_calculation
Revises: 0015_f22_document_entreprise
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0016_f23_score_calculation"
down_revision: str | None = "0015_f22_document_entreprise"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS score_calculation (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID NOT NULL REFERENCES account(id),
          entity_type TEXT NOT NULL,
          entity_id UUID NOT NULL,
          referentiel_id UUID NOT NULL REFERENCES referentiel(id),
          referentiel_version INT NOT NULL,
          referentiel_code TEXT NOT NULL,
          score_global NUMERIC(7,4) NULL,
          scores_by_pillar JSONB NOT NULL DEFAULT '{}'::jsonb,
          details_json JSONB NOT NULL DEFAULT '{}'::jsonb,
          coverage_ratio NUMERIC(5,4) NULL,
          computed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          computed_by UUID NULL REFERENCES account_user(id),
          CONSTRAINT chk_score_calc_entity_type
              CHECK (entity_type IN ('entreprise','projet')),
          CONSTRAINT chk_score_calc_score_range
              CHECK (score_global IS NULL OR (score_global >= 0 AND score_global <= 100)),
          CONSTRAINT chk_score_calc_coverage_range
              CHECK (coverage_ratio IS NULL OR (coverage_ratio >= 0 AND coverage_ratio <= 1))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_score_calc_lookup
        ON score_calculation(account_id, entity_type, entity_id,
                             referentiel_id, computed_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_score_calc_referentiel_code
        ON score_calculation(account_id, referentiel_code)
        WHERE score_global IS NOT NULL
        """
    )

    op.execute("GRANT SELECT, INSERT ON score_calculation TO app_user")
    op.execute("GRANT ALL ON score_calculation TO migrator")

    op.execute("ALTER TABLE score_calculation ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE score_calculation FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON score_calculation")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON score_calculation
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
    op.execute("DROP TABLE IF EXISTS score_calculation CASCADE")
