"""F08 — catalog: fonds_source, intermediaire, accreditation, offre.

Revision ID: 0008_catalog_fonds_offre
Revises: 0007_sources_canonical_url
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0008_catalog_fonds_offre"
down_revision: str | None = "0007_sources_canonical_url"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # ---------- Drop legacy F01 placeholder tables (incomplete schema) ----------
    # F01 a créé des squelettes de tables (fonds_source, intermediaire,
    # accreditation, offre, critere, document_requis) sans toutes les colonnes
    # F08. On les supprime pour les recréer avec le schéma complet F08.
    op.execute("DROP TABLE IF EXISTS critere CASCADE;")
    op.execute("DROP TABLE IF EXISTS document_requis CASCADE;")
    op.execute("DROP TABLE IF EXISTS offre CASCADE;")
    op.execute("DROP TABLE IF EXISTS accreditation CASCADE;")
    op.execute("DROP TABLE IF EXISTS intermediaire CASCADE;")
    op.execute("DROP TABLE IF EXISTS fonds_source CASCADE;")

    # ---------- ENUMs ----------
    op.execute(
        """
        DO $$ BEGIN
          CREATE TYPE fonds_type AS ENUM
            ('multilateral','bilateral','regional','national','prive');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
          CREATE TYPE submission_mode AS ENUM ('rolling','call_for_proposals');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
          CREATE TYPE intermediaire_type AS ENUM
            ('DAE','NIE','RIE','MIE','banque_locale','dev_carbone',
             'agence_nationale','agence_implem');
        EXCEPTION WHEN duplicate_object THEN NULL; END $$;
        """
    )
    # entity_status est représenté par CHECK constraint TEXT dans demo_indicator (F06).
    # Pour F08 on conserve la même approche TEXT + CHECK (incl. 'outdated').

    # ---------- helper function ----------
    op.execute(
        """
        CREATE OR REPLACE FUNCTION accreditation_is_active(
          valid_from DATE, valid_to DATE, at TIMESTAMPTZ DEFAULT now()
        ) RETURNS BOOLEAN AS $$
          SELECT valid_from <= at::date
             AND (valid_to IS NULL OR valid_to >= at::date)
        $$ LANGUAGE sql IMMUTABLE;
        """
    )

    # ---------- fonds_source ----------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS fonds_source (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            organisation TEXT NOT NULL DEFAULT '',
            type fonds_type NOT NULL DEFAULT 'multilateral',
            thematique TEXT[] NOT NULL DEFAULT '{}',
            instruments TEXT[] NOT NULL DEFAULT '{}',
            plafond_money JSONB NULL,
            plancher_money JSONB NULL,
            eligibilite_geo TEXT[] NOT NULL DEFAULT '{}',
            submission_mode submission_mode NOT NULL DEFAULT 'rolling',
            deadline TIMESTAMPTZ NULL,
            referentiel_id UUID NULL,
            criteres_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            documents_requis_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            frais_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            delais_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            site_url TEXT NULL,
            contact_json JSONB NULL,
            source_ids UUID[] NOT NULL DEFAULT '{}',
            version INT NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'draft'
              CHECK (status IN ('draft','published','archived','outdated','pending')),
            etag TEXT NOT NULL DEFAULT '',
            valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_to TIMESTAMPTZ NULL,
            logical_id UUID NOT NULL DEFAULT gen_random_uuid(),
            parent_id UUID NULL REFERENCES fonds_source(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID NULL REFERENCES account_user(id),
            published_by UUID NULL REFERENCES account_user(id),
            CONSTRAINT fonds_deadline_required_if_call CHECK (
              submission_mode <> 'call_for_proposals' OR deadline IS NOT NULL
            )
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_fonds_status_type ON fonds_source(status, type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fonds_thematique ON fonds_source USING gin(thematique);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fonds_instruments ON fonds_source USING gin(instruments);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fonds_geo ON fonds_source USING gin(eligibilite_geo);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fonds_name_trgm ON fonds_source USING gin(name gin_trgm_ops);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fonds_org_trgm ON fonds_source USING gin(organisation gin_trgm_ops);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_fonds_created_at_id ON fonds_source(created_at DESC, id DESC);")

    op.execute("ALTER TABLE fonds_source ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE fonds_source FORCE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS fonds_source_read ON fonds_source;")
    op.execute(
        """
        CREATE POLICY fonds_source_read ON fonds_source FOR SELECT
          USING (status = 'published' OR current_setting('app.is_admin', true) = 'true');
        """
    )
    op.execute("DROP POLICY IF EXISTS fonds_source_write ON fonds_source;")
    op.execute(
        """
        CREATE POLICY fonds_source_write ON fonds_source FOR ALL
          USING (current_setting('app.is_admin', true) = 'true')
          WITH CHECK (current_setting('app.is_admin', true) = 'true');
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON fonds_source TO app_user;")

    # ---------- intermediaire ----------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS intermediaire (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            name TEXT NOT NULL,
            type intermediaire_type NOT NULL,
            pays TEXT[] NOT NULL DEFAULT '{}',
            zone_op TEXT NULL,
            contact_json JSONB NULL,
            frais_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            delais_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            criteres_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            documents_requis_json JSONB NOT NULL DEFAULT '[]'::jsonb,
            referentiel_id UUID NULL,
            portail_url TEXT NULL,
            track_record_json JSONB NULL,
            source_ids UUID[] NOT NULL DEFAULT '{}',
            version INT NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'draft'
              CHECK (status IN ('draft','published','archived','outdated','pending')),
            etag TEXT NOT NULL DEFAULT '',
            valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_to TIMESTAMPTZ NULL,
            logical_id UUID NOT NULL DEFAULT gen_random_uuid(),
            parent_id UUID NULL REFERENCES intermediaire(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID NULL REFERENCES account_user(id),
            published_by UUID NULL REFERENCES account_user(id)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_inter_status_type ON intermediaire(status, type);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_inter_pays ON intermediaire USING gin(pays);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_inter_name_trgm ON intermediaire USING gin(name gin_trgm_ops);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_inter_created_at_id ON intermediaire(created_at DESC, id DESC);")
    op.execute("ALTER TABLE intermediaire ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE intermediaire FORCE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS intermediaire_read ON intermediaire;")
    op.execute(
        """
        CREATE POLICY intermediaire_read ON intermediaire FOR SELECT
          USING (status = 'published' OR current_setting('app.is_admin', true) = 'true');
        """
    )
    op.execute("DROP POLICY IF EXISTS intermediaire_write ON intermediaire;")
    op.execute(
        """
        CREATE POLICY intermediaire_write ON intermediaire FOR ALL
          USING (current_setting('app.is_admin', true) = 'true')
          WITH CHECK (current_setting('app.is_admin', true) = 'true');
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON intermediaire TO app_user;")

    # ---------- accreditation ----------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS accreditation (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            intermediaire_id UUID NOT NULL REFERENCES intermediaire(id),
            fonds_id UUID NOT NULL REFERENCES fonds_source(id),
            valid_from DATE NOT NULL,
            valid_to DATE NULL,
            plafond_money JSONB NULL,
            source_id UUID NOT NULL REFERENCES source(id),
            notes TEXT NULL,
            version INT NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'draft'
              CHECK (status IN ('draft','published','archived','outdated','pending')),
            etag TEXT NOT NULL DEFAULT '',
            valid_from_ts TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_to_ts TIMESTAMPTZ NULL,
            logical_id UUID NOT NULL DEFAULT gen_random_uuid(),
            parent_id UUID NULL REFERENCES accreditation(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID NULL REFERENCES account_user(id),
            published_by UUID NULL REFERENCES account_user(id)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_acc_inter_fonds_from ON accreditation(intermediaire_id, fonds_id, valid_from);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_acc_fonds_from ON accreditation(fonds_id, valid_from);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_acc_valid_to ON accreditation(valid_to);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_acc_created_at_id ON accreditation(created_at DESC, id DESC);")
    op.execute("ALTER TABLE accreditation ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE accreditation FORCE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS accreditation_read ON accreditation;")
    op.execute(
        """
        CREATE POLICY accreditation_read ON accreditation FOR SELECT
          USING (true);
        """
    )
    op.execute("DROP POLICY IF EXISTS accreditation_write ON accreditation;")
    op.execute(
        """
        CREATE POLICY accreditation_write ON accreditation FOR ALL
          USING (current_setting('app.is_admin', true) = 'true')
          WITH CHECK (current_setting('app.is_admin', true) = 'true');
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON accreditation TO app_user;")

    # ---------- offre ----------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS offre (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            fonds_id UUID NOT NULL REFERENCES fonds_source(id),
            intermediaire_id UUID NULL REFERENCES intermediaire(id),
            name TEXT NOT NULL DEFAULT '',
            accepted_languages TEXT[] NOT NULL DEFAULT ARRAY['fr'],
            deadline TIMESTAMPTZ NULL,
            criteres_offre_specifiques JSONB NOT NULL DEFAULT '[]'::jsonb,
            documents_specifiques JSONB NOT NULL DEFAULT '[]'::jsonb,
            frais_specifiques JSONB NOT NULL DEFAULT '{}'::jsonb,
            delais_specifiques JSONB NOT NULL DEFAULT '{}'::jsonb,
            effective_snapshot_hash TEXT NULL,
            needs_refresh BOOLEAN NOT NULL DEFAULT false,
            source_ids UUID[] NOT NULL DEFAULT '{}',
            version INT NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'draft'
              CHECK (status IN ('draft','published','archived','outdated','pending')),
            etag TEXT NOT NULL DEFAULT '',
            valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_to TIMESTAMPTZ NULL,
            logical_id UUID NOT NULL DEFAULT gen_random_uuid(),
            parent_id UUID NULL REFERENCES offre(id),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID NULL REFERENCES account_user(id),
            published_by UUID NULL REFERENCES account_user(id),
            CONSTRAINT uq_offre_fonds_inter_name UNIQUE (fonds_id, intermediaire_id, name)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_offre_status_pair ON offre(status, fonds_id, intermediaire_id);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_offre_needs_refresh ON offre(needs_refresh);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_offre_deadline ON offre(deadline);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_offre_created_at_id ON offre(created_at DESC, id DESC);")
    op.execute("ALTER TABLE offre ENABLE ROW LEVEL SECURITY;")
    op.execute("ALTER TABLE offre FORCE ROW LEVEL SECURITY;")
    op.execute("DROP POLICY IF EXISTS offre_read ON offre;")
    op.execute(
        """
        CREATE POLICY offre_read ON offre FOR SELECT
          USING (status = 'published' OR current_setting('app.is_admin', true) = 'true');
        """
    )
    op.execute("DROP POLICY IF EXISTS offre_write ON offre;")
    op.execute(
        """
        CREATE POLICY offre_write ON offre FOR ALL
          USING (current_setting('app.is_admin', true) = 'true')
          WITH CHECK (current_setting('app.is_admin', true) = 'true');
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON offre TO app_user;")


    # ---------- Re-créer critere & document_requis (placeholders F01/F09) ----------
    # F01 les avait créées comme placeholders ; F04 a ajouté versioning. F09 les
    # complétera. On les recrée ici avec le schéma F01+F04 minimal pour ne pas
    # casser les tests baseline F01-F07.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS critere (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          offre_id UUID NULL REFERENCES offre(id),
          referentiel_id UUID NULL REFERENCES referentiel(id),
          expression_json JSONB NULL,
          indicateur_ids UUID[] NULL,
          source_id UUID NULL REFERENCES source(id),
          created_by UUID NULL REFERENCES account_user(id),
          version INT NOT NULL DEFAULT 1,
          valid_from TIMESTAMPTZ NULL DEFAULT now(),
          valid_to TIMESTAMPTZ NULL,
          parent_id UUID NULL,
          logical_id UUID NOT NULL DEFAULT gen_random_uuid(),
          created_at TIMESTAMP NOT NULL DEFAULT now(),
          updated_at TIMESTAMP NOT NULL DEFAULT now(),
          CHECK (
            (offre_id IS NOT NULL AND referentiel_id IS NULL)
            OR (offre_id IS NULL AND referentiel_id IS NOT NULL)
          )
        );
        """
    )
    # F04 EXCLUDE constraint for versioning overlap (per logical_id).
    op.execute(
        """
        DO $do$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM pg_constraint WHERE conname = 'critere_no_overlap'
            ) THEN
                ALTER TABLE critere
                    ADD CONSTRAINT critere_no_overlap
                    EXCLUDE USING GIST (
                        logical_id WITH =,
                        tstzrange(valid_from, valid_to, '[)') WITH &&
                    );
            END IF;
        END $do$;
        """
    )

    # Recreate v_critere_verified view (dropped by CASCADE on critere).
    op.execute(
        """
        CREATE OR REPLACE VIEW v_critere_verified AS
          SELECT t.* FROM critere t
          JOIN source s ON s.id = t.source_id
          WHERE s.verification_status = 'verified';
        """
    )
    op.execute("GRANT SELECT ON v_critere_verified TO app_user")
    op.execute("GRANT SELECT ON v_critere_verified TO migrator")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_requis (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          fonds_id UUID NULL REFERENCES fonds_source(id),
          intermediaire_id UUID NULL REFERENCES intermediaire(id),
          name TEXT NOT NULL,
          source_id UUID NULL REFERENCES source(id),
          created_by UUID NULL REFERENCES account_user(id),
          created_at TIMESTAMP NOT NULL DEFAULT now(),
          updated_at TIMESTAMP NOT NULL DEFAULT now(),
          CHECK (fonds_id IS NOT NULL OR intermediaire_id IS NOT NULL)
        );
        """
    )
    # Recreate v_document_requis_verified view.
    op.execute(
        """
        CREATE OR REPLACE VIEW v_document_requis_verified AS
          SELECT t.* FROM document_requis t
          JOIN source s ON s.id = t.source_id
          WHERE s.verification_status = 'verified';
        """
    )
    op.execute("GRANT SELECT ON v_document_requis_verified TO app_user")
    op.execute("GRANT SELECT ON v_document_requis_verified TO migrator")


def downgrade() -> None:
    # Drop F08-recreated views FIRST (sinon F04 downgrade DROP COLUMN logical_id échoue).
    op.execute("DROP VIEW IF EXISTS v_critere_verified CASCADE;")
    op.execute("DROP VIEW IF EXISTS v_document_requis_verified CASCADE;")
    # Drop F08 catalog tables.
    op.execute("DROP TABLE IF EXISTS offre CASCADE;")
    op.execute("DROP TABLE IF EXISTS accreditation CASCADE;")
    op.execute("DROP TABLE IF EXISTS intermediaire CASCADE;")
    op.execute("DROP TABLE IF EXISTS fonds_source CASCADE;")
    # NOTE : on ne drop pas critere/document_requis ici — le downgrade F03/F01
    # s'en charge ; les vues v_*_verified ont déjà été drop ci-dessus pour
    # libérer la dépendance sur logical_id.
    op.execute("DROP FUNCTION IF EXISTS accreditation_is_active(DATE, DATE, TIMESTAMPTZ);")
    op.execute("DROP TYPE IF EXISTS intermediaire_type;")
    op.execute("DROP TYPE IF EXISTS submission_mode;")
    op.execute("DROP TYPE IF EXISTS fonds_type;")
