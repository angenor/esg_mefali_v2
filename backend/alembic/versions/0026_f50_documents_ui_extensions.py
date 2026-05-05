"""F50 — documents_ui_extensions.

Ajoute :
- colonnes sur ``document_entreprise`` :
    * content_sha256 BYTEA (32 octets)
    * extraction_payload JSONB DEFAULT '{}'
    * extraction_validated_at TIMESTAMPTZ
    * extraction_validated_by UUID
    * extraction_validation_payload JSONB
    * purge_scheduled_at TIMESTAMPTZ
- table ``document_link_projet`` (M:N — Q1) avec RLS tenant_isolation.
- index :
    * uq_document_entreprise_account_sha (partiel)
    * idx_document_entreprise_purge_scheduled
    * idx_document_link_projet_projet
    * idx_document_link_projet_document

Revision ID: 0026_f50_documents_ui_extensions
Revises: 0025_f42_email_verified
Create Date: 2026-05-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0026_f50_documents_ui_extensions"
down_revision: str | None = "0025_f42_email_verified"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. Colonnes additionnelles sur document_entreprise.
    op.execute(
        """
        ALTER TABLE document_entreprise
            ADD COLUMN IF NOT EXISTS content_sha256 BYTEA,
            ADD COLUMN IF NOT EXISTS extraction_payload JSONB NOT NULL DEFAULT '{}'::jsonb,
            ADD COLUMN IF NOT EXISTS extraction_validated_at TIMESTAMPTZ NULL,
            ADD COLUMN IF NOT EXISTS extraction_validated_by UUID NULL,
            ADD COLUMN IF NOT EXISTS extraction_validation_payload JSONB NULL,
            ADD COLUMN IF NOT EXISTS purge_scheduled_at TIMESTAMPTZ NULL
        """
    )

    op.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_document_entreprise_account_sha
            ON document_entreprise(account_id, content_sha256)
            WHERE deleted_at IS NULL AND content_sha256 IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_document_entreprise_purge_scheduled
            ON document_entreprise(purge_scheduled_at)
            WHERE deleted_at IS NOT NULL
        """
    )

    # 2. Table document_link_projet (M:N).
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_link_projet (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id UUID NOT NULL REFERENCES account(id),
            document_id UUID NOT NULL REFERENCES document_entreprise(id) ON DELETE CASCADE,
            projet_id UUID NOT NULL REFERENCES projet(id) ON DELETE CASCADE,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID NULL REFERENCES account_user(id),
            UNIQUE (document_id, projet_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_link_projet_projet "
        "ON document_link_projet(projet_id, account_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_document_link_projet_document "
        "ON document_link_projet(document_id)"
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON document_link_projet TO app_user")
    op.execute("GRANT ALL ON document_link_projet TO migrator")

    op.execute("ALTER TABLE document_link_projet ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE document_link_projet FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON document_link_projet")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON document_link_projet
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
    op.execute("DROP TABLE IF EXISTS document_link_projet CASCADE")
    op.execute("DROP INDEX IF EXISTS idx_document_entreprise_purge_scheduled")
    op.execute("DROP INDEX IF EXISTS uq_document_entreprise_account_sha")
    op.execute(
        """
        ALTER TABLE document_entreprise
            DROP COLUMN IF EXISTS purge_scheduled_at,
            DROP COLUMN IF EXISTS extraction_validation_payload,
            DROP COLUMN IF EXISTS extraction_validated_by,
            DROP COLUMN IF EXISTS extraction_validated_at,
            DROP COLUMN IF EXISTS extraction_payload,
            DROP COLUMN IF EXISTS content_sha256
        """
    )
