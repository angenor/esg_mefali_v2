"""F05 — Consent table with RLS, seed for existing accounts.

Revision ID: 0005b_consent_table
Revises: 0005a_audit_purge_trigger_and_jobs
Create Date: 2026-04-29

Implements T028: per-account granular consents with PME-scoped RLS.
Five kinds: mobile_money, exploitation_photos, public_attestation,
long_history, marketing. All seeded as ``given=false`` for existing
accounts (essential consents are out-of-scope here — the table only
tracks optional consents).
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0005b_consent_table"
down_revision: str | None = "0005a_audit_purge_jobs"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


CONSENT_KINDS = (
    "mobile_money",
    "exploitation_photos",
    "public_attestation",
    "long_history",
    "marketing",
)


def upgrade() -> None:
    # 1) Table consent
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS consent (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
            consent_kind TEXT NOT NULL CHECK (consent_kind IN
                ('mobile_money','exploitation_photos','public_attestation',
                 'long_history','marketing')),
            given BOOLEAN NOT NULL DEFAULT false,
            given_at TIMESTAMPTZ NULL,
            withdrawn_at TIMESTAMPTZ NULL,
            source_of_change TEXT NOT NULL CHECK (source_of_change IN
                ('manual','llm','import','admin')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            UNIQUE (account_id, consent_kind)
        );
        """
    )
    op.execute("CREATE INDEX IF NOT EXISTS idx_consent_account ON consent (account_id)")

    # 2) Trigger updated_at
    op.execute(
        """
        CREATE OR REPLACE FUNCTION consent_set_updated_at() RETURNS trigger AS $$
        BEGIN
          NEW.updated_at = now();
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS consent_updated_at_trg ON consent")
    op.execute(
        """
        CREATE TRIGGER consent_updated_at_trg
        BEFORE UPDATE ON consent
        FOR EACH ROW EXECUTE FUNCTION consent_set_updated_at();
        """
    )

    # 3) RLS PME-scoped
    op.execute("ALTER TABLE consent ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE consent FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS consent_tenant_isolation ON consent")
    op.execute(
        """
        CREATE POLICY consent_tenant_isolation ON consent
        FOR ALL
        USING (
            COALESCE(NULLIF(current_setting('app.is_admin', true), ''), 'false')::bool IS TRUE
            OR account_id = NULLIF(current_setting('app.current_account_id', true), '')::uuid
        )
        WITH CHECK (
            COALESCE(NULLIF(current_setting('app.is_admin', true), ''), 'false')::bool IS TRUE
            OR account_id = NULLIF(current_setting('app.current_account_id', true), '')::uuid
        );
        """
    )

    op.execute("REVOKE ALL ON consent FROM PUBLIC")
    op.execute("GRANT SELECT, INSERT, UPDATE ON consent TO app_user")

    # 4) Seed: pour tous les comptes existants, créer les 5 consentements
    # avec given=false. Idempotent grâce au UNIQUE.
    for kind in CONSENT_KINDS:
        op.execute(
            f"""
            INSERT INTO consent (account_id, consent_kind, given, source_of_change)
            SELECT id, '{kind}', false, 'admin'
            FROM account
            ON CONFLICT (account_id, consent_kind) DO NOTHING;
            """
        )

    # 5) Trigger AFTER INSERT ON account: créer auto les 5 consents pour
    # tout nouveau compte. Garantit l'invariant US2 « nouvelle PME -> 5
    # consentements optionnels seedés à given=false ».
    op.execute(
        """
        CREATE OR REPLACE FUNCTION account_seed_consents() RETURNS trigger AS $$
        BEGIN
          INSERT INTO consent (account_id, consent_kind, given, source_of_change)
          VALUES
            (NEW.id, 'mobile_money', false, 'admin'),
            (NEW.id, 'exploitation_photos', false, 'admin'),
            (NEW.id, 'public_attestation', false, 'admin'),
            (NEW.id, 'long_history', false, 'admin'),
            (NEW.id, 'marketing', false, 'admin')
          ON CONFLICT (account_id, consent_kind) DO NOTHING;
          RETURN NEW;
        END;
        $$ LANGUAGE plpgsql SECURITY DEFINER;
        """
    )
    op.execute("DROP TRIGGER IF EXISTS account_seed_consents_trg ON account")
    op.execute(
        """
        CREATE TRIGGER account_seed_consents_trg
        AFTER INSERT ON account
        FOR EACH ROW EXECUTE FUNCTION account_seed_consents();
        """
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER IF EXISTS account_seed_consents_trg ON account")
    op.execute("DROP FUNCTION IF EXISTS account_seed_consents()")
    op.execute("DROP TRIGGER IF EXISTS consent_updated_at_trg ON consent")
    op.execute("DROP FUNCTION IF EXISTS consent_set_updated_at()")
    op.execute("DROP TABLE IF EXISTS consent")
