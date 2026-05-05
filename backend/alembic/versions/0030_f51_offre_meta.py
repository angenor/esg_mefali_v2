"""F51 — Métadonnées catalogue pour le matching UI.

Étend le catalogue (offre + intermediaire + fonds_source) avec les champs
exposés par ``GET /me/offres`` et consommés par les cards `/matching` :

- ``offre.duree_min_mois SMALLINT NULL`` (∈ [1..240])
- ``offre.duree_max_mois SMALLINT NULL`` (∈ [1..240])
- ``offre.offre_type TEXT NULL`` ∈ {'credit','subvention','garantie','autre'}
  (override possible côté offre ; sinon fallback fonds_source.type)
- ``intermediaire.geo_lat NUMERIC(8,5) NULL`` ∈ [-90..90]
- ``intermediaire.geo_lng NUMERIC(8,5) NULL`` ∈ [-180..180]
- ``fonds_source.secteurs TEXT[] NULL`` (taxonomie lowercase ; complète
  ``thematique`` libre par une liste structurée pour le filtre `secteur`)

Tous les champs sont nullable pour rester rétrocompatibles avec le seed
existant ; le frontend dégrade gracieusement (label « Non spécifié », pin
absent sur la carte).

Revision ID: 0030_f51_offre_meta
Revises: 0029_f51_wizard_and_simulation_savee
Create Date: 2026-05-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0030_f51_offre_meta"
down_revision: str | None = "0029_f51_wizard_and_simulation_savee"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # 1. offre.duree_*_mois + offre.offre_type.
    op.execute(
        """
        ALTER TABLE offre
            ADD COLUMN IF NOT EXISTS duree_min_mois SMALLINT NULL,
            ADD COLUMN IF NOT EXISTS duree_max_mois SMALLINT NULL,
            ADD COLUMN IF NOT EXISTS offre_type TEXT NULL
        """
    )
    op.execute(
        "ALTER TABLE offre DROP CONSTRAINT IF EXISTS chk_offre_duree_min_mois"
    )
    op.execute(
        """
        ALTER TABLE offre
            ADD CONSTRAINT chk_offre_duree_min_mois
            CHECK (duree_min_mois IS NULL OR (duree_min_mois BETWEEN 1 AND 240))
        """
    )
    op.execute(
        "ALTER TABLE offre DROP CONSTRAINT IF EXISTS chk_offre_duree_max_mois"
    )
    op.execute(
        """
        ALTER TABLE offre
            ADD CONSTRAINT chk_offre_duree_max_mois
            CHECK (duree_max_mois IS NULL OR (duree_max_mois BETWEEN 1 AND 240))
        """
    )
    op.execute(
        "ALTER TABLE offre DROP CONSTRAINT IF EXISTS chk_offre_duree_minmax"
    )
    op.execute(
        """
        ALTER TABLE offre
            ADD CONSTRAINT chk_offre_duree_minmax
            CHECK (
                duree_min_mois IS NULL OR duree_max_mois IS NULL
                OR duree_min_mois <= duree_max_mois
            )
        """
    )
    op.execute(
        "ALTER TABLE offre DROP CONSTRAINT IF EXISTS chk_offre_offre_type"
    )
    op.execute(
        """
        ALTER TABLE offre
            ADD CONSTRAINT chk_offre_offre_type
            CHECK (offre_type IS NULL OR offre_type IN ('credit','subvention','garantie','autre'))
        """
    )

    # 2. intermediaire.geo_lat / geo_lng.
    op.execute(
        """
        ALTER TABLE intermediaire
            ADD COLUMN IF NOT EXISTS geo_lat NUMERIC(8,5) NULL,
            ADD COLUMN IF NOT EXISTS geo_lng NUMERIC(8,5) NULL
        """
    )
    op.execute(
        "ALTER TABLE intermediaire DROP CONSTRAINT IF EXISTS chk_intermediaire_geo_lat"
    )
    op.execute(
        """
        ALTER TABLE intermediaire
            ADD CONSTRAINT chk_intermediaire_geo_lat
            CHECK (geo_lat IS NULL OR (geo_lat BETWEEN -90 AND 90))
        """
    )
    op.execute(
        "ALTER TABLE intermediaire DROP CONSTRAINT IF EXISTS chk_intermediaire_geo_lng"
    )
    op.execute(
        """
        ALTER TABLE intermediaire
            ADD CONSTRAINT chk_intermediaire_geo_lng
            CHECK (geo_lng IS NULL OR (geo_lng BETWEEN -180 AND 180))
        """
    )
    op.execute(
        "ALTER TABLE intermediaire DROP CONSTRAINT IF EXISTS chk_intermediaire_geo_pair"
    )
    op.execute(
        """
        ALTER TABLE intermediaire
            ADD CONSTRAINT chk_intermediaire_geo_pair
            CHECK (
                (geo_lat IS NULL AND geo_lng IS NULL)
                OR (geo_lat IS NOT NULL AND geo_lng IS NOT NULL)
            )
        """
    )

    # 3. fonds_source.secteurs (taxonomie lowercase, complémentaire à thematique libre).
    op.execute(
        """
        ALTER TABLE fonds_source
            ADD COLUMN IF NOT EXISTS secteurs TEXT[] NULL
        """
    )

    # 4. Index pour filtres récurrents.
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_offre_offre_type
            ON offre(offre_type)
            WHERE offre_type IS NOT NULL
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS idx_fonds_source_secteurs
            ON fonds_source USING GIN (secteurs)
        """
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_fonds_source_secteurs")
    op.execute("DROP INDEX IF EXISTS idx_offre_offre_type")

    op.execute("ALTER TABLE fonds_source DROP COLUMN IF EXISTS secteurs")

    op.execute(
        """
        ALTER TABLE intermediaire
            DROP CONSTRAINT IF EXISTS chk_intermediaire_geo_pair,
            DROP CONSTRAINT IF EXISTS chk_intermediaire_geo_lng,
            DROP CONSTRAINT IF EXISTS chk_intermediaire_geo_lat,
            DROP COLUMN IF EXISTS geo_lng,
            DROP COLUMN IF EXISTS geo_lat
        """
    )

    op.execute(
        """
        ALTER TABLE offre
            DROP CONSTRAINT IF EXISTS chk_offre_offre_type,
            DROP CONSTRAINT IF EXISTS chk_offre_duree_minmax,
            DROP CONSTRAINT IF EXISTS chk_offre_duree_max_mois,
            DROP CONSTRAINT IF EXISTS chk_offre_duree_min_mois,
            DROP COLUMN IF EXISTS offre_type,
            DROP COLUMN IF EXISTS duree_max_mois,
            DROP COLUMN IF EXISTS duree_min_mois
        """
    )
