"""F19 — Skills engine: table skill + skill_source + ENUM skill_status.

Crée le schéma support du moteur de Skills (loader, fusion prompt). Le CRUD
admin et les seeds arrivent en F20/F21.

Revision ID: 0014_f19_skill
Revises: 0013_f18_chat_message_embedding_index
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0014_f19_skill"
down_revision: str | None = "0013_f18_chat_message_embedding_index"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Crée le type ENUM, la table skill et la table de liaison skill_source."""
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'skill_status') THEN
            CREATE TYPE skill_status AS ENUM ('draft','published');
          END IF;
        END$$;
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS skill (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          name TEXT NOT NULL,
          version INT NOT NULL DEFAULT 1,
          domain TEXT NOT NULL,
          prompt_expert TEXT NOT NULL,
          procedure TEXT NOT NULL DEFAULT '',
          tool_whitelist TEXT[] NOT NULL DEFAULT '{}',
          activation_rules JSONB NOT NULL DEFAULT '{}'::jsonb,
          golden_examples JSONB NOT NULL DEFAULT '[]'::jsonb,
          status skill_status NOT NULL DEFAULT 'draft',
          created_by UUID REFERENCES account_user(id),
          verified_by UUID REFERENCES account_user(id),
          valid_from TIMESTAMPTZ,
          valid_to TIMESTAMPTZ,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          CONSTRAINT skill_name_version_uniq UNIQUE (name, version)
        );
        """
    )

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS skill_source (
          skill_id UUID NOT NULL REFERENCES skill(id) ON DELETE CASCADE,
          source_id UUID NOT NULL REFERENCES source(id) ON DELETE RESTRICT,
          created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
          PRIMARY KEY (skill_id, source_id)
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS idx_skill_status ON skill(status);")
    op.execute("CREATE INDEX IF NOT EXISTS idx_skill_domain ON skill(domain);")
    op.execute(
        "CREATE INDEX IF NOT EXISTS idx_skill_source_source ON skill_source(source_id);"
    )


def downgrade() -> None:
    """Suppression idempotente."""
    op.execute("DROP TABLE IF EXISTS skill_source;")
    op.execute("DROP TABLE IF EXISTS skill;")
    op.execute("DROP TYPE IF EXISTS skill_status;")
