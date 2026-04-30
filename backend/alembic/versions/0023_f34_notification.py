"""F34 - notification table for PME notification center.

Revision ID: 0023_f34_notification
Revises: 0022_f33_url_patterns
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0023_f34_notification"
down_revision: str | None = "0022_f33_url_patterns"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS notification (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            account_id UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
            user_id UUID NULL REFERENCES account_user(id) ON DELETE SET NULL,
            kind TEXT NOT NULL,
            title TEXT NOT NULL,
            body TEXT NULL,
            entity_type TEXT NULL,
            entity_id UUID NULL,
            payload_json JSONB NULL,
            read_at TIMESTAMP NULL,
            version INT NOT NULL DEFAULT 1,
            deleted_at TIMESTAMP NULL,
            created_at TIMESTAMP NOT NULL DEFAULT now(),
            updated_at TIMESTAMP NOT NULL DEFAULT now(),
            CONSTRAINT chk_notification_kind CHECK (kind IN (
                'deadline_j_minus_30',
                'deadline_j_minus_7',
                'deadline_j_minus_1',
                'candidature_inactive',
                'offre_recommandee'
            ))
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notification_account_created "
        "ON notification(account_id, created_at DESC)"
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_notification_account_unread "
        "ON notification(account_id, read_at) WHERE deleted_at IS NULL"
    )
    # GRANTs (rôles applicatif/migrator) — sinon les sessions test échouent.
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON notification TO app_user")
    op.execute("GRANT ALL ON notification TO migrator")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS notification")
