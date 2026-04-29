"""F24 — Table rapport_genere (historique des rapports PDF) + RLS.

Revision ID: 0017_f24_rapport_genere
Revises: 0016_f23_score_calculation
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0017_f24_rapport_genere"
down_revision: str | None = "0016_f23_score_calculation"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS rapport_genere (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID NOT NULL REFERENCES account(id),
          entity_type TEXT NOT NULL,
          entity_id UUID NOT NULL,
          referentiels TEXT[] NOT NULL DEFAULT '{}'::text[],
          language TEXT NOT NULL DEFAULT 'fr',
          file_path TEXT NOT NULL,
          file_size_bytes INTEGER NULL,
          score_snapshot_json JSONB NOT NULL DEFAULT '{}'::jsonb,
          generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          generated_by UUID NULL REFERENCES account_user(id),
          CONSTRAINT chk_rapport_entity_type
              CHECK (entity_type IN ('entreprise','projet')),
          CONSTRAINT chk_rapport_language
              CHECK (language IN ('fr','en'))
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_rapport_genere_lookup
        ON rapport_genere(account_id, generated_at DESC)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_rapport_genere_entity
        ON rapport_genere(account_id, entity_type, entity_id, generated_at DESC)
        """
    )

    op.execute("GRANT SELECT, INSERT ON rapport_genere TO app_user")
    op.execute("GRANT ALL ON rapport_genere TO migrator")

    op.execute("ALTER TABLE rapport_genere ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE rapport_genere FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON rapport_genere")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON rapport_genere
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
    op.execute("DROP TABLE IF EXISTS rapport_genere CASCADE")
