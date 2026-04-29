"""F07 — Source canonical_url + unaccent + indices.

Revision ID: 0007_sources_canonical_url
Revises: 0006_f06_demo_indicator
Create Date: 2026-04-29

Ajouts (subset MVP P1) :
- extension ``unaccent`` (recherche accent-insensible, FR-016).
- colonne ``source.canonical_url TEXT`` (FR-002 / Q1) — backfill via
  copie de ``url`` (best-effort) puis NOT NULL.
- index unique ``ux_source_canonical_url_page`` (canonical_url, COALESCE(page,''))
  pour détecter les doublons (FR-003).
- indices secondaires ``idx_source_verification_status`` et
  ``idx_source_publisher`` pour la liste filtrée (US3).

NOTE — DEFERRED (Phase 9 polish) :
- colonne générée ``search_vector`` + index GIN (US3 perf < 1s sur 5000).
  L'index trigram existant (F03 ``source_search_idx``) couvre la recherche
  basique en attendant.
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_sources_canonical_url"
down_revision: str | None = "0006_f06_demo_indicator"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Extension unaccent (idempotente).
    op.execute("CREATE EXTENSION IF NOT EXISTS unaccent;")

    # Ajout colonne canonical_url, nullable au départ pour pouvoir backfill.
    op.add_column(
        "source",
        sa.Column("canonical_url", sa.Text(), nullable=True),
    )

    # Backfill : initialement, canonical_url = url. La canonicalisation
    # côté Python sera appliquée à la prochaine modification (idempotente).
    op.execute("UPDATE source SET canonical_url = url WHERE canonical_url IS NULL;")

    # Trigger BEFORE INSERT : si canonical_url est NULL, copie depuis url.
    # Compromis MVP : la colonne reste NULLable au niveau du schéma pour
    # ne pas casser les inserts hérités F03/F06 qui ne renseignent pas
    # canonical_url. Le service F07 garantit la canonicalisation Python.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION source_set_canonical_url()
        RETURNS TRIGGER AS $$
        BEGIN
          IF NEW.canonical_url IS NULL THEN
            NEW.canonical_url := NEW.url;
          END IF;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute(
        """
        CREATE TRIGGER trg_source_canonical_url_default
        BEFORE INSERT OR UPDATE ON source
        FOR EACH ROW EXECUTE FUNCTION source_set_canonical_url();
        """
    )

    # CHECK : canonical_url doit commencer par https:// (ou http:// pour les
    # données héritées) — assouplissement MVP. La canonicalisation Python
    # garantit https:// pour toute nouvelle source.
    op.execute(
        "ALTER TABLE source ADD CONSTRAINT ck_source_canonical_scheme "
        "CHECK (canonical_url IS NULL OR canonical_url ~ '^https?://');"
    )

    # Index unique sur (canonical_url, COALESCE(page,'')) pour la détection
    # de doublons. On utilise une expression via SQL brut.
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS ux_source_canonical_url_page "
        "ON source (canonical_url, COALESCE(page, ''));"
    )

    # Indices secondaires pour la liste filtrée.
    op.create_index(
        "idx_source_verification_status",
        "source",
        ["verification_status"],
        unique=False,
    )
    op.create_index(
        "idx_source_publisher",
        "source",
        ["publisher"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("idx_source_publisher", table_name="source")
    op.drop_index("idx_source_verification_status", table_name="source")
    op.execute("DROP INDEX IF EXISTS ux_source_canonical_url_page;")
    op.execute(
        "ALTER TABLE source DROP CONSTRAINT IF EXISTS ck_source_canonical_scheme;"
    )
    op.execute("DROP TRIGGER IF EXISTS trg_source_canonical_url_default ON source;")
    op.execute("DROP FUNCTION IF EXISTS source_set_canonical_url();")
    op.drop_column("source", "canonical_url")
    # On ne retire pas l'extension unaccent (peut être utilisée ailleurs).
