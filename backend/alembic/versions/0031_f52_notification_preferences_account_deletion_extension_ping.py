"""F52 - notification preferences + account deletion + extension ping + exports.

Crée :
- enums ``notification_channel``, ``deletion_status``, ``export_type``,
  ``export_status`` ;
- tables ``notification_preference``, ``account_deletion_request``,
  ``extension_ping``, ``export_artifact`` (toutes RLS-tenant) ;
- ALTER TABLE ``account_user`` : ``email_pending``,
  ``email_verification_token_hash``, ``email_verification_sent_at``.

Voir :file:`specs/052-notifications-settings-extension/data-model.md`.

Revision ID: 0031_f52_notif_prefs_deletion_extension_exports
Revises: 0030_f51_offre_meta
Create Date: 2026-05-05
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0031_f52_notif_prefs_deletion_extension_exports"
down_revision: str | None = "0030_f51_offre_meta"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:  # noqa: PLR0915 - migration linéaire, lisible séquentiellement
    # ------------------------------------------------------------------
    # 1. Enums (idempotents)
    # ------------------------------------------------------------------
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'notification_channel') THEN
                CREATE TYPE notification_channel AS ENUM ('email', 'in_app');
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'deletion_status') THEN
                CREATE TYPE deletion_status AS ENUM ('pending', 'cancelled', 'executed');
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'export_type') THEN
                CREATE TYPE export_type AS ENUM (
                    'rgpd_full', 'report_pdf', 'attestation_pdf', 'dossier_pdf'
                );
            END IF;
        END $$;
        """
    )
    op.execute(
        """
        DO $$ BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'export_status') THEN
                CREATE TYPE export_status AS ENUM ('pending', 'ready', 'expired', 'failed');
            END IF;
        END $$;
        """
    )

    # ------------------------------------------------------------------
    # 2. notification_preference (kind × channel × user)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification_preference (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES account_user(id) ON DELETE CASCADE,
            kind TEXT NOT NULL,
            channel notification_channel NOT NULL,
            enabled BOOLEAN NOT NULL DEFAULT TRUE,
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT chk_notification_preference_kind CHECK (kind IN (
                'deadline_j_minus_30',
                'deadline_j_minus_7',
                'deadline_j_minus_1',
                'candidature_inactive',
                'offre_recommandee',
                'system'
            )),
            CONSTRAINT uq_notification_preference UNIQUE (user_id, kind, channel)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notification_preference_account_user "
        "ON notification_preference(account_id, user_id)"
    )

    # ------------------------------------------------------------------
    # 3. account_deletion_request (workflow J+30)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS account_deletion_request (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES account_user(id) ON DELETE CASCADE,
            requested_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            scheduled_for TIMESTAMPTZ NOT NULL,
            status deletion_status NOT NULL DEFAULT 'pending',
            reason_motif TEXT NULL,
            confirmation_text TEXT NOT NULL,
            cancelled_at TIMESTAMPTZ NULL,
            executed_at TIMESTAMPTZ NULL
        )
        """
    )
    op.execute(
        "CREATE UNIQUE INDEX IF NOT EXISTS uq_account_deletion_pending "
        "ON account_deletion_request(account_id) WHERE status = 'pending'"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_account_deletion_status_scheduled "
        "ON account_deletion_request(status, scheduled_for)"
    )

    # ------------------------------------------------------------------
    # 4. extension_ping (UPSERT par user)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS extension_ping (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES account_user(id) ON DELETE CASCADE,
            extension_version TEXT NOT NULL,
            user_agent_summary TEXT NULL,
            last_ping_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            CONSTRAINT uq_extension_ping_user UNIQUE (user_id)
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_extension_ping_account_last_ping "
        "ON extension_ping(account_id, last_ping_at DESC)"
    )

    # ------------------------------------------------------------------
    # 5. export_artifact (historique exports)
    # ------------------------------------------------------------------
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS export_artifact (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
            user_id UUID NOT NULL REFERENCES account_user(id) ON DELETE CASCADE,
            type export_type NOT NULL,
            format TEXT NOT NULL,
            size_bytes BIGINT NULL,
            status export_status NOT NULL DEFAULT 'pending',
            signed_url TEXT NULL,
            signed_url_expires_at TIMESTAMPTZ NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            ready_at TIMESTAMPTZ NULL,
            delivered_via TEXT NULL,
            CONSTRAINT chk_export_artifact_format CHECK (format IN ('pdf', 'json')),
            CONSTRAINT chk_export_artifact_delivered_via CHECK (
                delivered_via IS NULL OR delivered_via IN ('inapp', 'email')
            )
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_export_artifact_account_created "
        "ON export_artifact(account_id, created_at DESC)"
    )

    # ------------------------------------------------------------------
    # 6. ALTER account_user — e-mail pending + verif token
    # ------------------------------------------------------------------
    op.execute(
        """
        ALTER TABLE account_user
            ADD COLUMN IF NOT EXISTS email_pending TEXT NULL,
            ADD COLUMN IF NOT EXISTS email_verification_token_hash TEXT NULL,
            ADD COLUMN IF NOT EXISTS email_verification_sent_at TIMESTAMPTZ NULL
        """
    )

    # ------------------------------------------------------------------
    # 7. RLS policies sur les nouvelles tables (gabarit *_tenant)
    # ------------------------------------------------------------------
    for tbl in (
        "notification_preference",
        "account_deletion_request",
        "extension_ping",
        "export_artifact",
    ):
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            DROP POLICY IF EXISTS {tbl}_tenant ON {tbl};
            CREATE POLICY {tbl}_tenant ON {tbl}
              USING (
                  account_id = current_setting('app.current_account_id', true)::uuid
                  OR current_setting('app.is_admin', true) = 'true'
              )
              WITH CHECK (
                  account_id = current_setting('app.current_account_id', true)::uuid
                  OR current_setting('app.is_admin', true) = 'true'
              );
            """
        )
        op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE ON {tbl} TO app_user")
        op.execute(f"GRANT ALL ON {tbl} TO migrator")


def downgrade() -> None:
    op.execute(
        """
        ALTER TABLE account_user
            DROP COLUMN IF EXISTS email_verification_sent_at,
            DROP COLUMN IF EXISTS email_verification_token_hash,
            DROP COLUMN IF EXISTS email_pending
        """
    )
    for tbl in (
        "export_artifact",
        "extension_ping",
        "account_deletion_request",
        "notification_preference",
    ):
        op.execute(f"DROP TABLE IF EXISTS {tbl} CASCADE")
    for enum in ("export_status", "export_type", "deletion_status", "notification_channel"):
        op.execute(f"DROP TYPE IF EXISTS {enum}")
