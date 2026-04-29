"""F12 — Enrichissement table projet + nouvelle table document_projet.

Ajoute (non destructif) sur projet :
- objectif_environnemental TEXT
- types_impact TEXT[]
- duree_mois INT
- structure_financement_arr TEXT[]
- localisation_pays_iso2 CHAR(2), localisation_ville TEXT
- CHECK statut/maturite/duree
- index (account_id, statut)

Cree table document_projet (RLS, account_id) avec contraintes.

Revision ID: 0012_f12_projets_documents
Revises: 0011_f13_chat_thread_message
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0012_f12_projets_documents"
down_revision: str | None = "0011_f13_chat_thread_message"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


PROJET_STATUTS = (
    "brouillon",
    "en_recherche_financement",
    "finance",
    "en_execution",
    "cloture",
)
PROJET_MATURITES = (
    "ideation",
    "pre_faisabilite",
    "pilote",
    "scale",
    "replication",
)
DOC_TYPES = (
    "faisabilite",
    "business_plan",
    "etude_impact",
    "lettre_soutien",
    "photo",
    "autre",
)


def upgrade() -> None:
    # --- Enrichissement projet ---
    op.execute("ALTER TABLE projet ADD COLUMN IF NOT EXISTS objectif_environnemental TEXT NULL")
    op.execute("ALTER TABLE projet ADD COLUMN IF NOT EXISTS types_impact TEXT[] NULL")
    op.execute("ALTER TABLE projet ADD COLUMN IF NOT EXISTS duree_mois INT NULL")
    op.execute(
        "ALTER TABLE projet ADD COLUMN IF NOT EXISTS structure_financement_arr TEXT[] NULL"
    )
    op.execute("ALTER TABLE projet ADD COLUMN IF NOT EXISTS localisation_pays_iso2 CHAR(2) NULL")
    op.execute("ALTER TABLE projet ADD COLUMN IF NOT EXISTS localisation_ville TEXT NULL")

    statut_list = ", ".join(f"'{s}'" for s in PROJET_STATUTS)
    op.execute("ALTER TABLE projet DROP CONSTRAINT IF EXISTS chk_projet_statut")
    op.execute(
        f"ALTER TABLE projet ADD CONSTRAINT chk_projet_statut "
        f"CHECK (statut IS NULL OR statut IN ({statut_list}))"
    )

    maturite_list = ", ".join(f"'{m}'" for m in PROJET_MATURITES)
    op.execute("ALTER TABLE projet DROP CONSTRAINT IF EXISTS chk_projet_maturite")
    op.execute(
        f"ALTER TABLE projet ADD CONSTRAINT chk_projet_maturite "
        f"CHECK (maturite IS NULL OR maturite IN ({maturite_list}))"
    )

    op.execute("ALTER TABLE projet DROP CONSTRAINT IF EXISTS chk_projet_duree_mois")
    op.execute(
        "ALTER TABLE projet ADD CONSTRAINT chk_projet_duree_mois "
        "CHECK (duree_mois IS NULL OR duree_mois >= 0)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_projet_account_statut "
        "ON projet(account_id, statut)"
    )

    # --- document_projet ---
    doc_types_list = ", ".join(f"'{d}'" for d in DOC_TYPES)
    op.execute(
        f"""
        CREATE TABLE IF NOT EXISTS document_projet (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID NOT NULL REFERENCES account(id),
          projet_id UUID NOT NULL REFERENCES projet(id) ON DELETE CASCADE,
          name TEXT NOT NULL,
          original_filename TEXT NOT NULL,
          mime_type TEXT NOT NULL,
          size_bytes BIGINT NOT NULL,
          type TEXT NOT NULL,
          storage_path TEXT NOT NULL,
          uploaded_by UUID NULL REFERENCES account_user(id),
          source_of_change TEXT NOT NULL DEFAULT 'manual',
          version INT NOT NULL DEFAULT 1,
          deleted_at TIMESTAMP NULL,
          created_at TIMESTAMP NOT NULL DEFAULT now(),
          updated_at TIMESTAMP NOT NULL DEFAULT now(),
          CONSTRAINT chk_document_projet_size CHECK (size_bytes BETWEEN 1 AND 26214400),
          CONSTRAINT chk_document_projet_type CHECK (type IN ({doc_types_list})),
          CONSTRAINT chk_document_projet_source CHECK (source_of_change IN ('manual','llm','import','admin'))
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_projet_projet_id "
        "ON document_projet(projet_id)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_document_projet_account_id "
        "ON document_projet(account_id)"
    )

    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON document_projet TO app_user")
    op.execute("GRANT ALL ON document_projet TO migrator")

    op.execute("ALTER TABLE document_projet ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE document_projet FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON document_projet")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON document_projet
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
    op.execute("DROP TABLE IF EXISTS document_projet CASCADE")

    op.execute("DROP INDEX IF EXISTS ix_projet_account_statut")
    op.execute("ALTER TABLE projet DROP CONSTRAINT IF EXISTS chk_projet_duree_mois")
    op.execute("ALTER TABLE projet DROP CONSTRAINT IF EXISTS chk_projet_maturite")
    op.execute("ALTER TABLE projet DROP CONSTRAINT IF EXISTS chk_projet_statut")
    op.execute("ALTER TABLE projet DROP COLUMN IF EXISTS localisation_ville")
    op.execute("ALTER TABLE projet DROP COLUMN IF EXISTS localisation_pays_iso2")
    op.execute("ALTER TABLE projet DROP COLUMN IF EXISTS structure_financement_arr")
    op.execute("ALTER TABLE projet DROP COLUMN IF EXISTS duree_mois")
    op.execute("ALTER TABLE projet DROP COLUMN IF EXISTS types_impact")
    op.execute("ALTER TABLE projet DROP COLUMN IF EXISTS objectif_environnemental")
