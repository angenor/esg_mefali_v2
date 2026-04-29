"""F30 - Table attestation + RLS.

Revision ID: 0020_f30_attestations
Revises: 0019_f29_credit
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0020_f30_attestations"
down_revision: str | None = "0019_f29_credit"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS attestation (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID NOT NULL REFERENCES account(id),
          entreprise_id UUID NOT NULL,
          public_id UUID NOT NULL UNIQUE DEFAULT gen_random_uuid(),
          scores_inclus_json JSONB NOT NULL,
          referentiels_versions_json JSONB NOT NULL,
          file_path TEXT NOT NULL,
          signature_ed25519 VARCHAR(256) NOT NULL,
          pubkey_fingerprint VARCHAR(64) NOT NULL,
          hash_document VARCHAR(64) NOT NULL,
          generated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          generated_by UUID NOT NULL,
          valid_until TIMESTAMPTZ NOT NULL,
          revoked_at TIMESTAMPTZ NULL,
          revoked_by UUID NULL,
          revoked_reason VARCHAR(500) NULL,
          version INTEGER NOT NULL DEFAULT 1
        )
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_attestation_account
        ON attestation(account_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_attestation_entreprise
        ON attestation(entreprise_id)
        """
    )
    op.execute(
        """
        CREATE INDEX IF NOT EXISTS ix_attestation_active_until
        ON attestation(valid_until)
        WHERE revoked_at IS NULL
        """
    )
    op.execute("GRANT SELECT, INSERT, UPDATE ON attestation TO app_user")
    op.execute("GRANT ALL ON attestation TO migrator")
    op.execute("ALTER TABLE attestation ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE attestation FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS tenant_isolation ON attestation")
    op.execute(
        """
        CREATE POLICY tenant_isolation ON attestation
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
    op.execute("DROP TABLE IF EXISTS attestation CASCADE")
