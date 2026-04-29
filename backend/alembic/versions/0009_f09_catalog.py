"""F09 — catalog: indicateur, referentiel + jonction, critere, document_requis, facteur_emission.

Drops legacy F01 placeholder tables and recreates them with the F09 schema:
columns required by F04 versioning (logical_id, valid_from, valid_to TIMESTAMPTZ,
parent_id) so the EXCLUDE USING gist constraint applied in 0004 keeps applying.

Revision ID: 0009_f09_catalog
Revises: 0008_catalog_fonds_offre
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0009_f09_catalog"
down_revision: str | None = "0008_catalog_fonds_offre"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


VERSIONED_F09 = (
    "indicateur",
    "referentiel",
    "critere",
    "document_requis",
    "facteur_emission",
)


def upgrade() -> None:
    # ------------------------------------------------------------------
    # 0) Drop legacy F01 placeholder tables (incomplete schema).
    #    F08 already dropped: critere, document_requis, offre, accreditation,
    #    intermediaire, fonds_source. Here we drop: referentiel, indicateur,
    #    facteur_emission, template (template kept as-is later if not used).
    # ------------------------------------------------------------------
    op.execute("DROP TABLE IF EXISTS indicateur_source CASCADE;")
    op.execute("DROP TABLE IF EXISTS referentiel_source CASCADE;")
    op.execute("DROP TABLE IF EXISTS referentiel_indicateur CASCADE;")
    op.execute("DROP TABLE IF EXISTS critere CASCADE;")
    op.execute("DROP TABLE IF EXISTS document_requis CASCADE;")
    op.execute("DROP TABLE IF EXISTS facteur_emission CASCADE;")
    op.execute("DROP TABLE IF EXISTS indicateur CASCADE;")
    op.execute("DROP TABLE IF EXISTS referentiel CASCADE;")

    # ------------------------------------------------------------------
    # 1) ENUMs (idempotent).
    # ------------------------------------------------------------------
    enum_specs = [
        ("pillar_enum", "('E','S','G','transverse')"),
        ("indicateur_value_type", "('numeric','percentage','boolean','enum','text')"),
        ("catalog_status_enum", "('draft','published','archived','outdated','pending')"),
        ("referentiel_type_enum", "('fonds','intermediaire','transverse','interne')"),
        ("referentiel_formula_enum", "('weighted_sum','custom')"),
        ("critere_owner_type_enum", "('fonds','intermediaire','offre','referentiel')"),
        ("critere_severity_enum", "('blocking','warning','info')"),
        ("document_owner_type_enum", "('fonds','intermediaire')"),
        ("document_type_enum", "('juridique','financier','technique','impact','autre')"),
        ("emission_scope_enum", "('1','2','3')"),
        (
            "emission_categorie_enum",
            "('energie','transport','dechets','achats','autre')",
        ),
    ]
    for name, vals in enum_specs:
        op.execute(
            f"DO $$ BEGIN CREATE TYPE {name} AS ENUM {vals}; "
            f"EXCEPTION WHEN duplicate_object THEN NULL; END $$;"
        )

    # ------------------------------------------------------------------
    # 2) indicateur (PIVOT, Module 0.7).
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE indicateur (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            definition TEXT NOT NULL DEFAULT '',
            pillar pillar_enum NOT NULL,
            unite TEXT NOT NULL DEFAULT '',
            value_type indicateur_value_type NOT NULL DEFAULT 'numeric',
            enum_values JSONB NULL,
            version INT NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'draft'
              CHECK (status IN ('draft','published','archived','outdated','pending')),
            etag TEXT NOT NULL DEFAULT '',
            valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_to TIMESTAMPTZ NULL,
            logical_id UUID NOT NULL DEFAULT gen_random_uuid(),
            parent_id UUID NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID NULL REFERENCES account_user(id),
            published_by UUID NULL REFERENCES account_user(id),
            CONSTRAINT indicateur_enum_values_required CHECK (
                value_type <> 'enum' OR (enum_values IS NOT NULL AND jsonb_array_length(enum_values) > 0)
            ),
            CONSTRAINT indicateur_code_format CHECK (code ~ '^[A-Z][A-Z0-9_]*$')
        );
        """
    )
    op.execute(
        "CREATE INDEX idx_indicateur_status_pillar ON indicateur(status, pillar);"
    )
    # Code uniqueness scoped to "active" rows (versioning friendly).
    op.execute(
        "CREATE UNIQUE INDEX idx_indicateur_code_active "
        "ON indicateur(code) WHERE status IN ('draft','published','pending');"
    )
    op.execute("CREATE INDEX idx_indicateur_created_at_id ON indicateur(created_at DESC, id DESC);")

    # indicateur_source (jonction)
    op.execute(
        """
        CREATE TABLE indicateur_source (
            indicateur_id UUID NOT NULL REFERENCES indicateur(id) ON DELETE CASCADE,
            source_id UUID NOT NULL REFERENCES source(id) ON DELETE RESTRICT,
            PRIMARY KEY (indicateur_id, source_id)
        );
        """
    )
    op.execute("CREATE INDEX idx_indicateur_source_src ON indicateur_source(source_id);")

    # ------------------------------------------------------------------
    # 3) referentiel + referentiel_source + referentiel_indicateur.
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE referentiel (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            publisher TEXT NOT NULL DEFAULT '',
            type referentiel_type_enum NOT NULL DEFAULT 'transverse',
            formula_type referentiel_formula_enum NOT NULL DEFAULT 'weighted_sum',
            formula_expression TEXT NULL,
            version INT NOT NULL DEFAULT 1,
            valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_to TIMESTAMPTZ NULL,
            status TEXT NOT NULL DEFAULT 'draft'
              CHECK (status IN ('draft','published','archived','outdated','pending')),
            etag TEXT NOT NULL DEFAULT '',
            logical_id UUID NOT NULL DEFAULT gen_random_uuid(),
            parent_id UUID NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID NULL REFERENCES account_user(id),
            published_by UUID NULL REFERENCES account_user(id),
            CONSTRAINT referentiel_formula_custom_required CHECK (
                formula_type <> 'custom' OR (formula_expression IS NOT NULL AND formula_expression <> '')
            )
        );
        """
    )
    op.execute("CREATE INDEX idx_referentiel_status_type ON referentiel(status, type);")
    op.execute("CREATE INDEX idx_referentiel_created_at_id ON referentiel(created_at DESC, id DESC);")
    op.execute(
        "CREATE UNIQUE INDEX idx_referentiel_code_active "
        "ON referentiel(code) WHERE status IN ('draft','published','pending');"
    )

    op.execute(
        """
        CREATE TABLE referentiel_source (
            referentiel_id UUID NOT NULL REFERENCES referentiel(id) ON DELETE CASCADE,
            source_id UUID NOT NULL REFERENCES source(id) ON DELETE RESTRICT,
            PRIMARY KEY (referentiel_id, source_id)
        );
        """
    )
    op.execute("CREATE INDEX idx_referentiel_source_src ON referentiel_source(source_id);")

    op.execute(
        """
        CREATE TABLE referentiel_indicateur (
            referentiel_id UUID NOT NULL REFERENCES referentiel(id) ON DELETE CASCADE,
            indicateur_id UUID NOT NULL REFERENCES indicateur(id) ON DELETE RESTRICT,
            poids NUMERIC(8,4) NOT NULL CHECK (poids >= 0),
            seuil_min NUMERIC(18,6) NULL,
            seuil_max NUMERIC(18,6) NULL,
            source_id UUID NOT NULL REFERENCES source(id),
            PRIMARY KEY (referentiel_id, indicateur_id)
        );
        """
    )

    # ------------------------------------------------------------------
    # 4) critere (DSL JSON sandboxé, owner polymorphe).
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE critere (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            owner_type critere_owner_type_enum NOT NULL,
            owner_id UUID NOT NULL,
            expression_json JSONB NOT NULL,
            label TEXT NOT NULL,
            severity critere_severity_enum NOT NULL DEFAULT 'warning',
            source_id UUID NOT NULL REFERENCES source(id),
            version INT NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'draft'
              CHECK (status IN ('draft','published','archived','outdated','pending')),
            etag TEXT NOT NULL DEFAULT '',
            valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_to TIMESTAMPTZ NULL,
            logical_id UUID NOT NULL DEFAULT gen_random_uuid(),
            parent_id UUID NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID NULL REFERENCES account_user(id),
            published_by UUID NULL REFERENCES account_user(id)
        );
        """
    )
    op.execute("CREATE INDEX idx_critere_owner ON critere(owner_type, owner_id);")
    op.execute("CREATE INDEX idx_critere_severity ON critere(severity);")
    op.execute("CREATE INDEX idx_critere_created_at_id ON critere(created_at DESC, id DESC);")

    # ------------------------------------------------------------------
    # 5) document_requis.
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE document_requis (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            owner_type document_owner_type_enum NOT NULL,
            owner_id UUID NOT NULL,
            name TEXT NOT NULL,
            description TEXT NULL,
            type document_type_enum NOT NULL DEFAULT 'autre',
            required_when JSONB NULL,
            source_id UUID NOT NULL REFERENCES source(id),
            version INT NOT NULL DEFAULT 1,
            status TEXT NOT NULL DEFAULT 'draft'
              CHECK (status IN ('draft','published','archived','outdated','pending')),
            etag TEXT NOT NULL DEFAULT '',
            valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_to TIMESTAMPTZ NULL,
            logical_id UUID NOT NULL DEFAULT gen_random_uuid(),
            parent_id UUID NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID NULL REFERENCES account_user(id),
            published_by UUID NULL REFERENCES account_user(id)
        );
        """
    )
    op.execute("CREATE INDEX idx_document_requis_owner ON document_requis(owner_type, owner_id);")
    op.execute("CREATE INDEX idx_document_requis_created_at_id ON document_requis(created_at DESC, id DESC);")

    # ------------------------------------------------------------------
    # 6) facteur_emission (UNIQUE + lookup index + valid_to trigger).
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE facteur_emission (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            code TEXT NOT NULL,
            name TEXT NOT NULL,
            valeur NUMERIC(18,6) NOT NULL CHECK (valeur >= 0),
            unite TEXT NOT NULL,
            pays_iso2 CHAR(2) NULL,
            scope emission_scope_enum NOT NULL,
            categorie emission_categorie_enum NOT NULL DEFAULT 'autre',
            source_id UUID NOT NULL REFERENCES source(id),
            version INT NOT NULL DEFAULT 1,
            valid_from_date DATE NOT NULL,
            valid_to_date DATE NULL,
            status TEXT NOT NULL DEFAULT 'draft'
              CHECK (status IN ('draft','published','archived','outdated','pending')),
            etag TEXT NOT NULL DEFAULT '',
            valid_from TIMESTAMPTZ NOT NULL DEFAULT now(),
            valid_to TIMESTAMPTZ NULL,
            logical_id UUID NOT NULL DEFAULT gen_random_uuid(),
            parent_id UUID NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_by UUID NULL REFERENCES account_user(id),
            published_by UUID NULL REFERENCES account_user(id),
            CONSTRAINT facteur_emission_unique_window UNIQUE (code, pays_iso2, valid_from_date)
        );
        """
    )
    # Lookup index (FR-007).
    op.execute(
        """
        CREATE INDEX idx_facteur_emission_lookup
          ON facteur_emission (code, pays_iso2, valid_from_date DESC);
        """
    )
    op.execute(
        "CREATE INDEX idx_facteur_emission_created_at_id "
        "ON facteur_emission (created_at DESC, id DESC);"
    )

    # Trigger BEFORE INSERT — auto-close previous window's valid_to_date.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION facteur_emission_close_prev() RETURNS trigger AS $body$
        BEGIN
            UPDATE facteur_emission
              SET valid_to_date = NEW.valid_from_date - INTERVAL '1 day',
                  updated_at = now()
              WHERE code = NEW.code
                AND COALESCE(pays_iso2, '~') = COALESCE(NEW.pays_iso2, '~')
                AND id <> NEW.id
                AND valid_from_date < NEW.valid_from_date
                AND (valid_to_date IS NULL OR valid_to_date >= NEW.valid_from_date);
            RETURN NEW;
        END;
        $body$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS facteur_emission_close_prev_trg ON facteur_emission;")
    op.execute(
        """
        CREATE TRIGGER facteur_emission_close_prev_trg
        AFTER INSERT ON facteur_emission
        FOR EACH ROW EXECUTE FUNCTION facteur_emission_close_prev();
        """
    )

    # ------------------------------------------------------------------
    # 7) RLS policies (admin + pme published).
    # ------------------------------------------------------------------
    rls_tables = [
        "indicateur",
        "referentiel",
        "referentiel_indicateur",
        "critere",
        "document_requis",
        "facteur_emission",
        "indicateur_source",
        "referentiel_source",
    ]
    for tbl in rls_tables:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY;")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY;")
        op.execute(f"DROP POLICY IF EXISTS {tbl}_read ON {tbl};")
        op.execute(f"DROP POLICY IF EXISTS {tbl}_write ON {tbl};")
        # Read: admin sees all; pme (default) sees published only on parent tables.
        if tbl in {"indicateur", "referentiel", "critere", "document_requis", "facteur_emission"}:
            op.execute(
                f"""
                CREATE POLICY {tbl}_read ON {tbl} FOR SELECT
                  USING (status = 'published' OR current_setting('app.is_admin', true) = 'true');
                """
            )
        else:
            # Junction tables: read open (parent FK already protects).
            op.execute(
                f"CREATE POLICY {tbl}_read ON {tbl} FOR SELECT USING (true);"
            )
        op.execute(
            f"""
            CREATE POLICY {tbl}_write ON {tbl} FOR ALL
              USING (current_setting('app.is_admin', true) = 'true')
              WITH CHECK (current_setting('app.is_admin', true) = 'true');
            """
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tbl} TO app_user;")
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tbl} TO migrator;")

    # ------------------------------------------------------------------
    # 7.5) Recreate ``v_<entity>_verified`` views (dropped by CASCADE on
    # legacy F01 placeholder tables). For ``indicateur`` the relation moves
    # to a junction table.
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE OR REPLACE VIEW v_indicateur_verified AS
          SELECT DISTINCT i.* FROM indicateur i
          JOIN indicateur_source isj ON isj.indicateur_id = i.id
          JOIN source s ON s.id = isj.source_id
          WHERE s.verification_status = 'verified';
        """
    )
    op.execute("GRANT SELECT ON v_indicateur_verified TO app_user;")
    op.execute("GRANT SELECT ON v_indicateur_verified TO migrator;")

    op.execute(
        """
        CREATE OR REPLACE VIEW v_critere_verified AS
          SELECT t.* FROM critere t
          JOIN source s ON s.id = t.source_id
          WHERE s.verification_status = 'verified';
        """
    )
    op.execute("GRANT SELECT ON v_critere_verified TO app_user;")
    op.execute("GRANT SELECT ON v_critere_verified TO migrator;")

    op.execute(
        """
        CREATE OR REPLACE VIEW v_document_requis_verified AS
          SELECT t.* FROM document_requis t
          JOIN source s ON s.id = t.source_id
          WHERE s.verification_status = 'verified';
        """
    )
    op.execute("GRANT SELECT ON v_document_requis_verified TO app_user;")
    op.execute("GRANT SELECT ON v_document_requis_verified TO migrator;")

    op.execute(
        """
        CREATE OR REPLACE VIEW v_facteur_emission_verified AS
          SELECT t.* FROM facteur_emission t
          JOIN source s ON s.id = t.source_id
          WHERE s.verification_status = 'verified';
        """
    )
    op.execute("GRANT SELECT ON v_facteur_emission_verified TO app_user;")
    op.execute("GRANT SELECT ON v_facteur_emission_verified TO migrator;")

    # ------------------------------------------------------------------
    # 8) FK parent_id self-reference + EXCLUDE constraint (re-apply F04).
    # ------------------------------------------------------------------
    for tbl in VERSIONED_F09:
        op.execute(
            f"ALTER TABLE {tbl} "
            f"ADD CONSTRAINT fk_{tbl}_parent FOREIGN KEY (parent_id) REFERENCES {tbl}(id);"
        )
        op.execute(
            f"""
            ALTER TABLE {tbl}
              ADD CONSTRAINT {tbl}_logical_no_overlap
              EXCLUDE USING gist (
                logical_id WITH =,
                tstzrange(valid_from, valid_to) WITH &&
              );
            """
        )
        op.execute(
            f"CREATE INDEX {tbl}_logical_active_idx "
            f"ON {tbl} (logical_id) WHERE valid_to IS NULL;"
        )


def downgrade() -> None:
    # Drop F09 views first.
    for v in (
        "v_indicateur_verified",
        "v_critere_verified",
        "v_document_requis_verified",
        "v_facteur_emission_verified",
    ):
        op.execute(f"DROP VIEW IF EXISTS {v} CASCADE;")

    rls_tables = [
        "indicateur_source",
        "referentiel_source",
        "facteur_emission",
        "document_requis",
        "critere",
        "referentiel_indicateur",
        "referentiel",
        "indicateur",
    ]
    for tbl in rls_tables:
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE;")
    op.execute("DROP FUNCTION IF EXISTS facteur_emission_close_prev() CASCADE;")

    # Recreate legacy F01/F08 placeholder schemas so downstream downgrades
    # (F08, F03) keep working.
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS referentiel (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name TEXT NOT NULL,
          version TEXT NOT NULL,
          valid_from DATE NULL,
          valid_to DATE NULL,
          status TEXT NULL,
          created_by UUID NULL REFERENCES account_user(id),
          created_at TIMESTAMP NOT NULL DEFAULT now(),
          updated_at TIMESTAMP NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS indicateur (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name TEXT NOT NULL,
          definition TEXT NULL,
          unite TEXT NULL,
          status TEXT NULL,
          source_id UUID NULL REFERENCES source(id),
          created_by UUID NULL REFERENCES account_user(id),
          created_at TIMESTAMP NOT NULL DEFAULT now(),
          updated_at TIMESTAMP NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS critere (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          offre_id UUID NULL,
          referentiel_id UUID NULL REFERENCES referentiel(id),
          expression_json JSONB NULL,
          indicateur_ids UUID[] NULL,
          source_id UUID NULL REFERENCES source(id),
          created_by UUID NULL REFERENCES account_user(id),
          created_at TIMESTAMP NOT NULL DEFAULT now(),
          updated_at TIMESTAMP NOT NULL DEFAULT now(),
          CHECK (
            (offre_id IS NOT NULL AND referentiel_id IS NULL)
            OR (offre_id IS NULL AND referentiel_id IS NOT NULL)
          )
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS document_requis (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          fonds_id UUID NULL,
          intermediaire_id UUID NULL,
          name TEXT NOT NULL,
          source_id UUID NULL REFERENCES source(id),
          created_by UUID NULL REFERENCES account_user(id),
          created_at TIMESTAMP NOT NULL DEFAULT now(),
          updated_at TIMESTAMP NOT NULL DEFAULT now(),
          CHECK (fonds_id IS NOT NULL OR intermediaire_id IS NOT NULL)
        );
        """
    )
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS facteur_emission (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name TEXT NOT NULL,
          valeur NUMERIC(18,6) NOT NULL,
          unite TEXT NOT NULL,
          pays TEXT NULL,
          source_id UUID NULL REFERENCES source(id),
          version INT NOT NULL DEFAULT 1,
          created_by UUID NULL REFERENCES account_user(id),
          created_at TIMESTAMP NOT NULL DEFAULT now(),
          updated_at TIMESTAMP NOT NULL DEFAULT now()
        );
        """
    )
    # Recreate legacy v_<tbl>_verified views (F03 expects them on downgrade).
    for tbl in ("indicateur", "critere", "document_requis", "facteur_emission"):
        op.execute(
            f"""
            CREATE OR REPLACE VIEW v_{tbl}_verified AS
              SELECT t.* FROM {tbl} t
              JOIN source s ON s.id = t.source_id
              WHERE s.verification_status = 'verified';
            """
        )
        op.execute(f"GRANT SELECT ON v_{tbl}_verified TO app_user;")
        op.execute(f"GRANT SELECT ON v_{tbl}_verified TO migrator;")
    for name, _vals in [
        ("emission_categorie_enum", ""),
        ("emission_scope_enum", ""),
        ("document_type_enum", ""),
        ("document_owner_type_enum", ""),
        ("critere_severity_enum", ""),
        ("critere_owner_type_enum", ""),
        ("referentiel_formula_enum", ""),
        ("referentiel_type_enum", ""),
        ("indicateur_value_type", ""),
        ("pillar_enum", ""),
    ]:
        op.execute(f"DROP TYPE IF EXISTS {name};")
