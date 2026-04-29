"""F06 — demo_indicator table + RLS + indices.

Revision ID: 0006_f06_demo_indicator
Revises: 0005b_consent_table
Create Date: 2026-04-29

Adds:
- pg_trgm extension (idempotent).
- ``demo_indicator`` table (cf. data-model.md §1) — démo back-office, déprécié par F09.
- RLS policies: read public for ``status='published'``, read+write all for admin.
- BTREE keyset index + trigram GIN indexes on (name, publisher, external_id).

NOTE: ``audit_log.account_id`` is already nullable (cf. F04). Aucune modif requise.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_f06_demo_indicator"
down_revision: str | None = "0005b_consent_table"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm;")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS demo_indicator (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            external_id TEXT NULL,
            publisher TEXT NULL,
            description TEXT NULL,
            unit TEXT NULL,
            source_id UUID NOT NULL REFERENCES source(id),
            status TEXT NOT NULL DEFAULT 'draft' CHECK (status IN ('draft','published','outdated','pending')),
            version INT NOT NULL DEFAULT 1,
            valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_to TIMESTAMPTZ NULL,
            logical_id UUID NOT NULL DEFAULT gen_random_uuid(),
            parent_id UUID NULL REFERENCES demo_indicator(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID NOT NULL REFERENCES account_user(id),
            published_by UUID NULL REFERENCES account_user(id)
        );
        """
    )

    op.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_demo_indicator_external_id ON demo_indicator(external_id) WHERE external_id IS NOT NULL AND valid_to IS NULL;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_indicator_status ON demo_indicator(status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_indicator_created_at_id ON demo_indicator(created_at DESC, id DESC);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_indicator_name_trgm ON demo_indicator USING gin (name gin_trgm_ops);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_indicator_publisher_trgm ON demo_indicator USING gin (publisher gin_trgm_ops);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_demo_indicator_external_id_trgm ON demo_indicator USING gin (external_id gin_trgm_ops);")

    # RLS
    op.execute("ALTER TABLE demo_indicator ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE demo_indicator FORCE ROW LEVEL SECURITY;")
    op.execute(
        """
        DROP POLICY IF EXISTS demo_indicator_read ON demo_indicator;
        CREATE POLICY demo_indicator_read ON demo_indicator
          FOR SELECT
          USING (status = 'published' OR current_setting('app.is_admin', true) = 'true');
        """
    )
    op.execute(
        """
        DROP POLICY IF EXISTS demo_indicator_write ON demo_indicator;
        CREATE POLICY demo_indicator_write ON demo_indicator
          FOR ALL
          USING (current_setting('app.is_admin', true) = 'true')
          WITH CHECK (current_setting('app.is_admin', true) = 'true');
        """
    )

    # Grant base privileges to app_user (RLS still applies).
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON demo_indicator TO app_user;")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS demo_indicator CASCADE;")
