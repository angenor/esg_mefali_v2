"""F13 — Table chat_thread + enrichissement chat_message (thread_id, context_json).

Non destructif :
- Crée la table ``chat_thread`` avec RLS forcée.
- Ajoute à ``chat_message`` les colonnes ``thread_id`` (FK chat_thread, ON DELETE
  CASCADE) et ``context_json`` (JSONB).
- Ajoute la CHECK ``role IN ('user','assistant','system','tool')``.
- Ajoute les index utiles à la pagination et au tri par updated_at.

Revision ID: 0011_f13_chat_thread_message
Revises: 0010_f11_entreprise_enrich
Create Date: 2026-04-29
"""

from __future__ import annotations

from collections.abc import Sequence

from alembic import op

revision: str = "0011_f13_chat_thread_message"
down_revision: str | None = "0010_f11_entreprise_enrich"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # --- chat_thread ---
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS chat_thread (
          id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
          account_id UUID NOT NULL REFERENCES account(id),
          user_id UUID NULL REFERENCES account_user(id),
          title TEXT NOT NULL,
          archived BOOLEAN NOT NULL DEFAULT FALSE,
          version INT NOT NULL DEFAULT 1,
          deleted_at TIMESTAMP NULL,
          created_at TIMESTAMP NOT NULL DEFAULT now(),
          updated_at TIMESTAMP NOT NULL DEFAULT now()
        )
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chat_thread_account_user "
        "ON chat_thread(account_id, user_id, archived, updated_at DESC)"
    )

    op.execute("ALTER TABLE chat_thread ENABLE ROW LEVEL SECURITY")
    op.execute("ALTER TABLE chat_thread FORCE ROW LEVEL SECURITY")
    op.execute("DROP POLICY IF EXISTS chat_thread_account_isolation ON chat_thread")
    op.execute(
        """
        CREATE POLICY chat_thread_account_isolation ON chat_thread
        USING (account_id = current_setting('app.current_account_id', true)::uuid)
        WITH CHECK (account_id = current_setting('app.current_account_id', true)::uuid)
        """
    )

    # --- chat_message ALTER (non destructif) ---
    op.execute("ALTER TABLE chat_message ADD COLUMN IF NOT EXISTS thread_id UUID NULL")
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'fk_chat_message_thread'
              AND table_name = 'chat_message'
          ) THEN
            ALTER TABLE chat_message
              ADD CONSTRAINT fk_chat_message_thread
              FOREIGN KEY (thread_id) REFERENCES chat_thread(id) ON DELETE CASCADE;
          END IF;
        END $$;
        """
    )
    op.execute("ALTER TABLE chat_message ADD COLUMN IF NOT EXISTS context_json JSONB NULL")
    op.execute(
        """
        DO $$
        BEGIN
          IF NOT EXISTS (
            SELECT 1 FROM information_schema.table_constraints
            WHERE constraint_name = 'chat_message_role_check'
              AND table_name = 'chat_message'
          ) THEN
            ALTER TABLE chat_message
              ADD CONSTRAINT chat_message_role_check
              CHECK (role IN ('user','assistant','system','tool'));
          END IF;
        END $$;
        """
    )
    op.execute(
        "CREATE INDEX IF NOT EXISTS ix_chat_message_thread_created "
        "ON chat_message(thread_id, created_at)"
    )


def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS ix_chat_message_thread_created")
    op.execute("ALTER TABLE chat_message DROP CONSTRAINT IF EXISTS chat_message_role_check")
    op.execute("ALTER TABLE chat_message DROP COLUMN IF EXISTS context_json")
    op.execute("ALTER TABLE chat_message DROP CONSTRAINT IF EXISTS fk_chat_message_thread")
    op.execute("ALTER TABLE chat_message DROP COLUMN IF EXISTS thread_id")

    op.execute("DROP POLICY IF EXISTS chat_thread_account_isolation ON chat_thread")
    op.execute("DROP INDEX IF EXISTS ix_chat_thread_account_user")
    op.execute("DROP TABLE IF EXISTS chat_thread")
