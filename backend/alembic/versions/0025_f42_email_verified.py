"""F42 US4 — account_user.email_verified_at.

Revision ID: 0025_f42_email_verified
Revises: 0024_f42_user_preferences
Create Date: 2026-05-03
"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy import inspect

from alembic import op

revision: str = "0025_f42_email_verified"
down_revision: str | None = "0024_f42_user_preferences"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("account_user")}
    if "email_verified_at" not in cols:
        op.add_column(
            "account_user",
            sa.Column("email_verified_at", sa.DateTime(timezone=True), nullable=True),
        )


def downgrade() -> None:
    bind = op.get_bind()
    insp = inspect(bind)
    cols = {c["name"] for c in insp.get_columns("account_user")}
    if "email_verified_at" in cols:
        op.drop_column("account_user", "email_verified_at")
