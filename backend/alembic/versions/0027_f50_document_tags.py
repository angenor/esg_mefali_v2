"""F50 US5 — colonne tags TEXT[] sur document_entreprise.

Permet l'édition inline de tags (chips) côté UI ; recherche client tolérante
aux accents s'appuie sur ce champ.

Revision ID: 0027_f50_document_tags
Revises: 0026_f50_documents_ui_extensions
Create Date: 2026-05-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0027_f50_document_tags"
down_revision: str | None = "0026_f50_documents_ui_extensions"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        ALTER TABLE document_entreprise
            ADD COLUMN IF NOT EXISTS tags TEXT[] NOT NULL DEFAULT '{}'::TEXT[]
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_entreprise_tags "
        "ON document_entreprise USING GIN (tags)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_document_entreprise_tags")
    op.execute("ALTER TABLE document_entreprise DROP COLUMN IF EXISTS tags")
