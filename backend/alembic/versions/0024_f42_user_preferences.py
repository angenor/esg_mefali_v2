"""F42 — user_preferences + tokens_invalidated_at.

Revision ID: 0024_f42_user_preferences
Revises: 0023_f34_notification
Create Date: 2026-05-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision: str = "0024_f42_user_preferences"
down_revision: str | None = "0023_f34_notification"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    # 1) Enum onboarding_state — créé idempotent
    op.execute(
        """
        DO $$ BEGIN
            CREATE TYPE onboarding_state AS ENUM ('pending', 'completed', 'skipped', 'dismissed');
        EXCEPTION
            WHEN duplicate_object THEN NULL;
        END $$;
        """
    )

    # 2) Table user_preferences
    if not insp.has_table("user_preferences"):
        op.execute(
            """
            CREATE TABLE user_preferences (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                user_id UUID NOT NULL UNIQUE REFERENCES account_user(id) ON DELETE CASCADE,
                account_id UUID NOT NULL REFERENCES account(id) ON DELETE CASCADE,
                onboarding_state onboarding_state NOT NULL DEFAULT 'pending',
                onboarding_state_updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
            )
            """
        )
        op.execute(
            "CREATE INDEX idx_user_preferences_account_id "
            "ON user_preferences(account_id)"
        )
        op.execute("ALTER TABLE user_preferences ENABLE ROW LEVEL SECURITY")
        op.execute(
            """
            CREATE POLICY user_preferences_tenant_isolation ON user_preferences
            USING (account_id = current_setting('app.current_account_id')::uuid)
            """
        )
        op.execute(
            "GRANT SELECT, INSERT, UPDATE, DELETE ON user_preferences TO app_user"
        )
        op.execute("GRANT ALL ON user_preferences TO migrator")

    # 3) account_user.tokens_invalidated_at — ajouté seulement si absent
    cols = {c["name"] for c in insp.get_columns("account_user")}
    if "tokens_invalidated_at" not in cols:
        op.add_column(
            "account_user",
            sa.Column("tokens_invalidated_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)

    cols = {c["name"] for c in insp.get_columns("account_user")}
    if "tokens_invalidated_at" in cols:
        op.drop_column("account_user", "tokens_invalidated_at")

    if insp.has_table("user_preferences"):
        op.execute("DROP TABLE user_preferences")

    op.execute("DROP TYPE IF EXISTS onboarding_state")
