"""F11 — Enrichissement table entreprise pour le profil PME.

Ajoute (non destructif) :
- secteur_code TEXT, secteur_label TEXT
- localisation_siege_pays_iso2 CHAR(2), localisation_siege_ville TEXT
- zones_operation_pays_iso2 TEXT[]
- gouvernance_json JSONB
- contrainte UNIQUE (account_id) — abort si doublons existants

Conserve les colonnes historiques (secteur, localisation, gouvernance).

Revision ID: 0010_f11_entreprise_enrich
Revises: 0009_f09_catalog
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0010_f11_entreprise_enrich"
down_revision: str | None = "0009_f09_catalog"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        DO $$
        DECLARE
            dup_count INT;
        BEGIN
            SELECT COUNT(*) INTO dup_count FROM (
                SELECT account_id FROM entreprise
                GROUP BY account_id HAVING COUNT(*) > 1
            ) t;
            IF dup_count > 0 THEN
                RAISE EXCEPTION 'F11 migration aborted: % accounts with multiple entreprise rows', dup_count;
            END IF;
        END
        $$;
        """
    )

    op.execute("ALTER TABLE entreprise ADD COLUMN IF NOT EXISTS secteur_code TEXT NULL")
    op.execute("ALTER TABLE entreprise ADD COLUMN IF NOT EXISTS secteur_label TEXT NULL")
    op.execute(
        "ALTER TABLE entreprise ADD COLUMN IF NOT EXISTS localisation_siege_pays_iso2 CHAR(2) NULL"
    )
    op.execute(
        "ALTER TABLE entreprise ADD COLUMN IF NOT EXISTS localisation_siege_ville TEXT NULL"
    )
    op.execute(
        "ALTER TABLE entreprise ADD COLUMN IF NOT EXISTS zones_operation_pays_iso2 TEXT[] NULL"
    )
    op.execute("ALTER TABLE entreprise ADD COLUMN IF NOT EXISTS gouvernance_json JSONB NULL")

    op.execute("ALTER TABLE entreprise DROP CONSTRAINT IF EXISTS uq_entreprise_account_id")
    op.execute(
        "ALTER TABLE entreprise ADD CONSTRAINT uq_entreprise_account_id UNIQUE (account_id)"
    )

    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_entreprise_secteur_code ON entreprise(secteur_code)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_entreprise_secteur_code")
    op.execute("ALTER TABLE entreprise DROP CONSTRAINT IF EXISTS uq_entreprise_account_id")
    op.execute("ALTER TABLE entreprise DROP COLUMN IF EXISTS gouvernance_json")
    op.execute("ALTER TABLE entreprise DROP COLUMN IF EXISTS zones_operation_pays_iso2")
    op.execute("ALTER TABLE entreprise DROP COLUMN IF EXISTS localisation_siege_ville")
    op.execute("ALTER TABLE entreprise DROP COLUMN IF EXISTS localisation_siege_pays_iso2")
    op.execute("ALTER TABLE entreprise DROP COLUMN IF EXISTS secteur_label")
    op.execute("ALTER TABLE entreprise DROP COLUMN IF EXISTS secteur_code")
