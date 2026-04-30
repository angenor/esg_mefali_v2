"""F33 - url_pattern + field_mapping_intermediaire pour l'extension Chrome.

Revision ID: 0022_f33_url_patterns
Revises: 0021_f31_action_plan
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0022_f33_url_patterns"
down_revision: str | None = "0021_f31_action_plan"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS url_pattern (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            pattern TEXT NOT NULL,
            pattern_type TEXT NOT NULL DEFAULT 'wildcard'
              CHECK (pattern_type IN ('wildcard','regex')),
            nature TEXT NOT NULL
              CHECK (nature IN ('fonds','intermediaire')),
            fonds_id UUID NULL REFERENCES fonds_source(id) ON DELETE SET NULL,
            intermediaire_id UUID NULL REFERENCES intermediaire(id) ON DELETE SET NULL,
            offre_id UUID NULL REFERENCES offre(id) ON DELETE SET NULL,
            is_active BOOLEAN NOT NULL DEFAULT TRUE,
            preferred_language VARCHAR(2) NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_url_pattern_active ON url_pattern(is_active)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_url_pattern_offre ON url_pattern(offre_id)"
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS field_mapping_intermediaire (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            intermediaire_id UUID NOT NULL REFERENCES intermediaire(id) ON DELETE CASCADE,
            mapping_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_field_mapping_intermediaire UNIQUE (intermediaire_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_field_mapping_intermediaire_inter "
        "ON field_mapping_intermediaire(intermediaire_id)"
    )


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS field_mapping_intermediaire")
    op.execute("DROP TABLE IF EXISTS url_pattern")
