"""F22 — Nouvelle table document_entreprise (parallele a document_projet F12).

Cree :
- table document_entreprise (RLS, account_id, contraintes CHECK)
- indexes (entreprise_id, account_id)
- GRANTs app_user / migrator
- RLS policy tenant_isolation (calque F12)

Revision ID: 0015_f22_document_entreprise
Revises: 0014_f19_skill
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0015_f22_document_entreprise"
down_revision: str | None = "0014_f19_skill"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


DOC_TYPES = (
    "statuts",
    "rapport_activite",
    "facture",
    "contrat",
    "politique",
    "autre",
)

OCR_STATUSES = (
    "pending",
    "done",
    "deferred",
    "failed",
)


def upgrade() -> None:
    doc_types_list = ", ".join(f"'{d}'" for d in DOC_TYPES)
    ocr_status_list = ", ".join(f"'{s}'" for s in OCR_STATUSES)

    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS document_entreprise (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID NOT NULL REFERENCES account(id),
          entreprise_id UUID NOT NULL REFERENCES entreprise(id) ON DELETE CASCADE,
          name TEXT NOT NULL,
          original_filename TEXT NOT NULL,
          mime_type TEXT NOT NULL,
          size_bytes BIGINT NOT NULL,
          type TEXT NOT NULL,
          storage_path TEXT NOT NULL,
          text_content TEXT NULL,
          ocr_status TEXT NOT NULL DEFAULT 'pending',
          ocr_error TEXT NULL,
          uploaded_by UUID NULL REFERENCES account_user(id),
          source_of_change TEXT NOT NULL DEFAULT 'manual',
          version INT NOT NULL DEFAULT 1,
          deleted_at TIMESTAMP NULL,
          created_at TIMESTAMP NOT NULL DEFAULT now(),
          updated_at TIMESTAMP NOT NULL DEFAULT now(),
          CONSTRAINT chk_document_entreprise_size
              CHECK (size_bytes BETWEEN 1 AND 26214400),
          CONSTRAINT chk_document_entreprise_type
              CHECK (type IN ({doc_types_list})),
          CONSTRAINT chk_document_entreprise_ocr_status
              CHECK (ocr_status IN ({ocr_status_list})),
          CONSTRAINT chk_document_entreprise_source
              CHECK (source_of_change IN ('manual','llm','import','admin'))
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_entreprise_entreprise_id "
        "ON document_entreprise(entreprise_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_entreprise_account_id "
        "ON document_entreprise(account_id)"
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON document_entreprise TO app_user")
    op.execute("GRANT ALL ON document_entreprise TO migrator")

    op.execute("ALTER TABLE document_entreprise ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE document_entreprise FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON document_entreprise")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON document_entreprise
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
    op.execute("DROP TABLE IF EXISTS document_entreprise CASCADE")
