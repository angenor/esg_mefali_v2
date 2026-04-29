"""F03 — Source anti-hallucination : table source renforcée + unsourced_claim_log
+ vues v_<entity>_verified + RLS.

Revision ID: 0003_source_anti_hallucination
Revises: 0002_auth_rls
Create Date: 2026-04-29

Contenu :
- Enum ``source_verification_status`` (pending/verified/outdated/rejected).
- Renforce la table ``source`` (existante en F01 avec colonnes faibles) :
  * url NOT NULL + CHECK ``^https?://``
  * publisher NOT NULL
  * captured_at NOT NULL DEFAULT now()
  * captured_by NOT NULL FK account_user
  * verified_by FK account_user
  * verified_at TIMESTAMPTZ
  * verification_status -> ENUM, NOT NULL, DEFAULT 'pending'
  * embedding vector(1024) NULL (NOT NULL via CHECK quand verified)
  * tsv tsvector GENERATED
  * status_version BIGINT NOT NULL DEFAULT 1
  * notes TEXT
  * CHECK : verified -> verified_by, verified_at, embedding requis
- Triggers :
  * BEFORE UPDATE : double validation FR-013 (verified_by != captured_by lors transition vers verified)
  * BEFORE UPDATE : incrément status_version + insertion audit_log lors changement de verification_status
- Indexes : GIN tsv, IVFFlat embedding, status, publisher.
- Vues v_<entity>_verified pour : indicateur, critere, document_requis, facteur_emission, referentiel
  (formule, seuil non créées en F01 — vues différées en F09).
- Table unsourced_claim_log + RLS (account_id = current_setting('app.current_account_id')::uuid).

Note convention : on s'aligne sur ``app.current_account_id`` posé par F02 dans
``backend/app/auth/dependencies.py`` plutôt que sur ``app.account_id`` mentionné
dans le data-model F03 — la convention F02 est en place, on conserve la
compatibilité.
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0003_source_anti_hallucination"
down_revision: str | None = "0002_auth_rls"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Tables catalogue déjà existantes en F01 portant `source_id UUID NULL REFERENCES source(id)`.
# F03 ne renforce PAS le NOT NULL sur ces colonnes (data backfill = F07/F09)
# mais crée les vues v_<entity>_verified qui filtrent sur verification_status.
CATALOG_TABLES = (
    "indicateur",
    "critere",
    "document_requis",
    "facteur_emission",
    # ``referentiel``, ``formule``, ``seuil`` n'ont pas de colonne
    # ``source_id`` en F01 — vues différées en F09 (catalogue référentiels).
)


def upgrade() -> None:
    # 1) Enum verification_status
    op.execute(
        """
        DO $do$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'source_verification_status') THEN
                CREATE TYPE source_verification_status AS ENUM
                    ('pending', 'verified', 'outdated', 'rejected');
            END IF;
        END
        $do$;
        """
    )

    # 2) Renforcer table source (existante en F01 avec colonnes laxes)
    # Ajouter colonnes manquantes
    op.execute(
        "ALTER TABLE source "
        "ADD COLUMN IF NOT EXISTS verified_at TIMESTAMPTZ NULL, "
        "ADD COLUMN IF NOT EXISTS notes TEXT NULL, "
        "ADD COLUMN IF NOT EXISTS embedding vector(1024) NULL, "
        "ADD COLUMN IF NOT EXISTS status_version BIGINT NOT NULL DEFAULT 1"
    )

    # tsv generated column (idempotent : drop si existe en NULL puis recrée)
    op.execute(
        """
        DO $do$
        BEGIN
            IF NOT EXISTS (
                SELECT 1 FROM information_schema.columns
                WHERE table_name='source' AND column_name='tsv'
            ) THEN
                ALTER TABLE source ADD COLUMN tsv tsvector
                  GENERATED ALWAYS AS (
                    to_tsvector('french',
                      coalesce(title,'') || ' ' ||
                      coalesce(publisher,'') || ' ' ||
                      coalesce(notes,'')
                    )
                  ) STORED;
            END IF;
        END
        $do$;
        """
    )

    # Backfill captured_at NULL avant NOT NULL
    op.execute("UPDATE source SET captured_at = COALESCE(captured_at, now())")

    # Backfill captured_by NULL via 1er admin disponible (sinon laisse NULL : fail volontaire)
    op.execute(
        """
        DO $do$
        DECLARE
            v_admin uuid;
        BEGIN
            SELECT id INTO v_admin FROM account_user WHERE role = 'admin' LIMIT 1;
            IF v_admin IS NOT NULL THEN
                UPDATE source SET captured_by = v_admin WHERE captured_by IS NULL;
            END IF;
        END
        $do$;
        """
    )

    # Convertir verification_status TEXT -> enum
    op.execute(
        "UPDATE source SET verification_status = 'pending' "
        "WHERE verification_status IS NULL OR verification_status NOT IN "
        "('pending','verified','outdated','rejected')"
    )
    op.execute(
        "ALTER TABLE source "
        "ALTER COLUMN verification_status TYPE source_verification_status "
        "USING verification_status::source_verification_status"
    )
    op.execute(
        "ALTER TABLE source "
        "ALTER COLUMN verification_status SET DEFAULT 'pending', "
        "ALTER COLUMN verification_status SET NOT NULL"
    )

    # NOT NULL sur url, publisher, captured_at, captured_by — ne forcer que si data déjà valide
    op.execute("ALTER TABLE source ALTER COLUMN title SET NOT NULL")
    op.execute(
        """
        DO $do$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM source WHERE url IS NULL) THEN
                ALTER TABLE source ALTER COLUMN url SET NOT NULL;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM source WHERE publisher IS NULL) THEN
                ALTER TABLE source ALTER COLUMN publisher SET NOT NULL;
            END IF;
            IF NOT EXISTS (SELECT 1 FROM source WHERE captured_by IS NULL) THEN
                ALTER TABLE source ALTER COLUMN captured_by SET NOT NULL;
            END IF;
        END
        $do$;
        """
    )
    op.execute("ALTER TABLE source ALTER COLUMN captured_at SET NOT NULL")
    op.execute("ALTER TABLE source ALTER COLUMN captured_at SET DEFAULT now()")

    # FK captured_by / verified_by -> account_user déjà posées en F01
    # (``fk_source_captured_by`` / ``fk_source_verified_by``). Rien à faire ici.

    # CHECK url
    op.execute(
        """
        ALTER TABLE source DROP CONSTRAINT IF EXISTS chk_source_url_https;
        ALTER TABLE source ADD CONSTRAINT chk_source_url_https
          CHECK (url IS NULL OR url ~ '^https?://');
        """
    )

    # CHECK verified state
    op.execute(
        """
        ALTER TABLE source DROP CONSTRAINT IF EXISTS chk_source_verified_state;
        ALTER TABLE source ADD CONSTRAINT chk_source_verified_state
          CHECK (
            verification_status <> 'verified'
            OR (verified_by IS NOT NULL AND verified_at IS NOT NULL AND embedding IS NOT NULL)
          );
        """
    )

    # 3) Triggers
    # Double validation : verified_by != captured_by lors transition vers verified.
    op.execute(
        """
        CREATE OR REPLACE FUNCTION source_double_validation_trg()
        RETURNS trigger AS $body$
        BEGIN
            IF (TG_OP = 'UPDATE'
                AND OLD.verification_status IS DISTINCT FROM NEW.verification_status
                AND NEW.verification_status = 'verified')
            THEN
                IF NEW.verified_by IS NULL THEN
                    RAISE EXCEPTION 'verified_by required when transitioning to verified';
                END IF;
                IF NEW.verified_by = NEW.captured_by THEN
                    RAISE EXCEPTION 'double validation required: verified_by must differ from captured_by';
                END IF;
                IF NEW.verified_at IS NULL THEN
                    NEW.verified_at := now();
                END IF;
            END IF;
            RETURN NEW;
        END;
        $body$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS source_double_validation ON source")
    op.execute(
        """
        CREATE TRIGGER source_double_validation
        BEFORE UPDATE ON source
        FOR EACH ROW
        EXECUTE FUNCTION source_double_validation_trg();
        """
    )

    # Incrément status_version + audit
    op.execute(
        """
        CREATE OR REPLACE FUNCTION source_status_version_trg()
        RETURNS trigger AS $body$
        BEGIN
            IF (TG_OP = 'UPDATE'
                AND OLD.verification_status IS DISTINCT FROM NEW.verification_status)
            THEN
                NEW.status_version := COALESCE(OLD.status_version, 1) + 1;
                INSERT INTO audit_log
                  (id, user_id, account_id, entity_type, entity_id,
                   field, old_value, new_value, source_of_change)
                VALUES
                  (gen_random_uuid(), NEW.verified_by, NULL, 'source', NEW.id,
                   'verification_status',
                   to_jsonb(OLD.verification_status::text),
                   to_jsonb(NEW.verification_status::text),
                   'admin');
            END IF;
            RETURN NEW;
        END;
        $body$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS source_status_version ON source")
    op.execute(
        """
        CREATE TRIGGER source_status_version
        BEFORE UPDATE ON source
        FOR EACH ROW
        EXECUTE FUNCTION source_status_version_trg();
        """
    )

    # 4) Indexes
    op.execute("CREATE INDEX IF NOT EXISTS source_tsv_gin ON source USING gin(tsv)")
    op.execute(
        "CREATE INDEX IF NOT EXISTS source_embedding_ivf ON source "
        "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
    )
    op.execute("CREATE INDEX IF NOT EXISTS source_status_idx ON source(verification_status)")
    op.execute("CREATE INDEX IF NOT EXISTS source_publisher_idx ON source(publisher)")

    # 5) Vues v_<entity>_verified
    for tbl in CATALOG_TABLES:
        op.execute(
            f"""
            CREATE OR REPLACE VIEW v_{tbl}_verified AS
            SELECT t.* FROM {tbl} t
            JOIN source s ON s.id = t.source_id
            WHERE s.verification_status = 'verified';
            """
        )
        op.execute(f"GRANT SELECT ON v_{tbl}_verified TO app_user")
        op.execute(f"GRANT SELECT ON v_{tbl}_verified TO migrator")

    # 6) Table unsourced_claim_log
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS unsourced_claim_log (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
            user_id UUID NULL REFERENCES account_user(id) ON DELETE SET NULL,
            claim_text TEXT NOT NULL,
            claim_text_normalized TEXT GENERATED ALWAYS AS (lower(trim(claim_text))) STORED,
            context_json JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS unsourced_claim_log_agg_idx "
        "ON unsourced_claim_log (account_id, claim_text_normalized)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS unsourced_claim_log_created_idx "
        "ON unsourced_claim_log (account_id, created_at DESC)"
    )

    # 7) RLS sur unsourced_claim_log : politique INSERT + SELECT
    op.execute("ALTER TABLE unsourced_claim_log ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE unsourced_claim_log FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON unsourced_claim_log")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON unsourced_claim_log
        USING (
            COALESCE(NULLIF(current_setting('app.is_admin', true), ''), 'false')::bool IS TRUE
            OR account_id = NULLIF(current_setting('app.current_account_id', true), '')::uuid
        )
        WITH CHECK (
            account_id = NULLIF(current_setting('app.current_account_id', true), '')::uuid
        );
        """
    )

    # GRANT INSERT/SELECT à app_user, REVOKE UPDATE/DELETE
    op.execute("GRANT SELECT, INSERT ON unsourced_claim_log TO app_user")
    op.execute("REVOKE UPDATE, DELETE ON unsourced_claim_log FROM app_user")
    op.execute("GRANT ALL ON unsourced_claim_log TO migrator")


def downgrade() -> None:
    # Nettoyage : sources créées en test/dev par des admins (account_id IS NULL)
    # Les enfants (indicateur, etc.) ne référencent pas avec ON DELETE RESTRICT
    # en F01 — la suppression cascade par défaut se fait via la FK F01 NULL.
    # Note : on supprime aussi les indicateurs/critères/etc. liés.
    for tbl in CATALOG_TABLES:
        op.execute(
            f"DELETE FROM {tbl} WHERE source_id IN "
            f"(SELECT id FROM source WHERE captured_by IN "
            f"(SELECT id FROM account_user WHERE account_id IS NULL))"
        )
    op.execute(
        "DELETE FROM source WHERE captured_by IN "
        "(SELECT id FROM account_user WHERE account_id IS NULL) "
        "OR verified_by IN (SELECT id FROM account_user WHERE account_id IS NULL)"
    )
    # Vues
    for tbl in CATALOG_TABLES:
        op.execute(f"DROP VIEW IF EXISTS v_{tbl}_verified")

    # unsourced_claim_log
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON unsourced_claim_log")
    op.execute("DROP TABLE IF EXISTS unsourced_claim_log")

    # Triggers source
    op.execute("DROP TRIGGER IF EXISTS source_status_version ON source")
    op.execute("DROP FUNCTION IF EXISTS source_status_version_trg()")
    op.execute("DROP TRIGGER IF EXISTS source_double_validation ON source")
    op.execute("DROP FUNCTION IF EXISTS source_double_validation_trg()")

    # Indexes
    op.execute("DROP INDEX IF EXISTS source_publisher_idx")
    op.execute("DROP INDEX IF EXISTS source_status_idx")
    op.execute("DROP INDEX IF EXISTS source_embedding_ivf")
    op.execute("DROP INDEX IF EXISTS source_tsv_gin")

    # Constraints
    op.execute("ALTER TABLE source DROP CONSTRAINT IF EXISTS chk_source_verified_state")
    op.execute("ALTER TABLE source DROP CONSTRAINT IF EXISTS chk_source_url_https")
    # FK F01 conservées (fk_source_*) — non touchées par F03.

    # verification_status -> TEXT
    op.execute(
        "ALTER TABLE source ALTER COLUMN verification_status DROP DEFAULT, "
        "ALTER COLUMN verification_status DROP NOT NULL"
    )
    op.execute(
        "ALTER TABLE source ALTER COLUMN verification_status TYPE TEXT "
        "USING verification_status::text"
    )

    # Drop colonnes ajoutées
    op.execute(
        "ALTER TABLE source "
        "DROP COLUMN IF EXISTS tsv, "
        "DROP COLUMN IF EXISTS status_version, "
        "DROP COLUMN IF EXISTS embedding, "
        "DROP COLUMN IF EXISTS notes, "
        "DROP COLUMN IF EXISTS verified_at"
    )

    op.execute("DROP TYPE IF EXISTS source_verification_status")
