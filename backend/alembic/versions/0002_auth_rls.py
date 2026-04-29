"""F02 — Auth tables + Row-Level Security.

Revision ID: 0002_auth_rls
Revises: 0001_initial_schema
Create Date: 2026-04-29

Contenu :
- Création des rôles SQL `app_user` (RLS appliquée) et `migrator` (BYPASS RLS)
  si manquants. Les passwords sont lus depuis env (APP_USER_PASSWORD,
  MIGRATOR_PASSWORD). Sinon, mot de passe placeholder.
- Type ENUM `account_user_role`.
- ALTER TABLE `account_user` : ajoute `role`, `last_login_at`, rend
  `account_id` nullable, ajoute CHECK admin/pme.
- CREATE TABLE `refresh_tokens`, `password_reset_tokens`.
- ENABLE + FORCE Row-Level Security sur toutes les tables `account_id NOT NULL`
  (entreprise, projet, candidature, chat_message) et politique
  `tenant_isolation` (USING + WITH CHECK).
- Politiques équivalentes par `user_id` sur `refresh_tokens` /
  `password_reset_tokens`.
"""

from __future__ import annotations

import os
from collections.abc import Sequence

from alembic import op

revision: str = "0002_auth_rls"
down_revision: str | None = "0001_initial_schema"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# Tables F01 portant `account_id NOT NULL` à protéger par RLS.
# Note : `account_user` reste hors RLS (besoin d'accès non scopé pour
# register/login). Les hashes bcrypt protègent les credentials et l'email
# n'est pas sensible.
ACCOUNT_SCOPED_TABLES = (
    "entreprise",
    "projet",
    "candidature",
    "chat_message",
)


def _create_roles_if_missing() -> None:
    """Crée app_user et migrator si absents.

    Si les passwords env sont vides, on logue un warning mais on continue : la
    DB de dev peut déjà avoir les rôles via le script init.
    """
    app_pwd = os.environ.get("APP_USER_PASSWORD", "").replace("'", "''")
    mig_pwd = os.environ.get("MIGRATOR_PASSWORD", "").replace("'", "''")
    op.execute(
        f"""
        DO $do$
        BEGIN
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'app_user') THEN
                EXECUTE 'CREATE ROLE app_user LOGIN PASSWORD ''{app_pwd or 'app_user_change_me'}''';
            END IF;
            IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'migrator') THEN
                EXECUTE 'CREATE ROLE migrator LOGIN PASSWORD ''{mig_pwd or 'migrator_change_me'}'' BYPASSRLS';
            END IF;
        END
        $do$;
        """
    )

    # Permissions
    op.execute("GRANT USAGE ON SCHEMA public TO app_user")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user")
    op.execute("GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO app_user")
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO app_user"
    )
    op.execute(
        "ALTER DEFAULT PRIVILEGES IN SCHEMA public "
        "GRANT USAGE, SELECT ON SEQUENCES TO app_user"
    )

    op.execute("GRANT USAGE, CREATE ON SCHEMA public TO migrator")
    op.execute("GRANT ALL ON ALL TABLES IN SCHEMA public TO migrator")
    op.execute("GRANT ALL ON ALL SEQUENCES IN SCHEMA public TO migrator")


def upgrade() -> None:
    # 1) Rôles SQL
    _create_roles_if_missing()

    # 2) ENUM role
    op.execute(
        """
        DO $do$
        BEGIN
            IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'account_user_role') THEN
                CREATE TYPE account_user_role AS ENUM ('pme', 'admin');
            END IF;
        END
        $do$;
        """
    )

    # 3) Étendre account_user (singular en F01)
    op.execute("ALTER TABLE account_user ALTER COLUMN account_id DROP NOT NULL")
    op.execute(
        "ALTER TABLE account_user ADD COLUMN IF NOT EXISTS last_login_at TIMESTAMPTZ NULL"
    )
    # `role` existe déjà en TEXT NULL en F01 ; on le convertit proprement.
    op.execute("UPDATE account_user SET role = 'pme' WHERE role IS NULL OR role NOT IN ('pme','admin')")
    op.execute(
        "ALTER TABLE account_user "
        "ALTER COLUMN role TYPE account_user_role USING role::account_user_role"
    )
    op.execute(
        "ALTER TABLE account_user "
        "ALTER COLUMN role SET DEFAULT 'pme', ALTER COLUMN role SET NOT NULL"
    )
    op.execute(
        """
        ALTER TABLE account_user
        ADD CONSTRAINT chk_admin_account
        CHECK ((role = 'pme' AND account_id IS NOT NULL)
            OR (role = 'admin' AND account_id IS NULL))
        """
    )

    # 4) refresh_tokens
    op.execute(
        """
        CREATE TABLE refresh_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES account_user(id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL UNIQUE,
            parent_id UUID NULL REFERENCES refresh_tokens(id) ON DELETE SET NULL,
            issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL,
            used_at TIMESTAMPTZ NULL,
            revoked_at TIMESTAMPTZ NULL,
            revoked_reason TEXT NULL
        )
        """
    )
    op.execute("CREATE INDEX idx_refresh_tokens_user_id ON refresh_tokens(user_id)")
    op.execute(
        "CREATE INDEX idx_refresh_tokens_active ON refresh_tokens(user_id) "
        "WHERE used_at IS NULL AND revoked_at IS NULL"
    )

    # 5) password_reset_tokens
    op.execute(
        """
        CREATE TABLE password_reset_tokens (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID NOT NULL REFERENCES account_user(id) ON DELETE CASCADE,
            token_hash TEXT NOT NULL UNIQUE,
            issued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            expires_at TIMESTAMPTZ NOT NULL,
            consumed_at TIMESTAMPTZ NULL
        )
        """
    )
    op.execute(
        "CREATE INDEX idx_password_reset_tokens_user_id ON password_reset_tokens(user_id)"
    )

    # 6) Permissions sur les nouvelles tables
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON refresh_tokens TO app_user")
    op.execute("GRANT SELECT, INSERT, UPDATE, DELETE ON password_reset_tokens TO app_user")
    op.execute("GRANT ALL ON refresh_tokens TO migrator")
    op.execute("GRANT ALL ON password_reset_tokens TO migrator")

    # 7) RLS sur tables account-scoped
    for tbl in ACCOUNT_SCOPED_TABLES:
        op.execute(f"ALTER TABLE {tbl} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} FORCE ROW LEVEL SECURITY")
        op.execute(
            f"""
            CREATE POLICY tenant_isolation ON {tbl}
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

    # 8) refresh_tokens / password_reset_tokens : pas de RLS — la sécurité est
    # assurée par le hash opaque (token_hash) et les requêtes WHERE token_hash=…
    # Les opérer en RLS empêcherait register/login (pas de contexte avant émission).


def downgrade() -> None:
    # Désactive RLS et supprime les policies (ordre inverse)
    for tbl in ("refresh_tokens", "password_reset_tokens"):
        op.execute(f"DROP POLICY IF EXISTS {tbl}_owner ON {tbl}")
    for tbl in ACCOUNT_SCOPED_TABLES:
        op.execute(f"DROP POLICY IF EXISTS tenant_isolation ON {tbl}")
        op.execute(f"ALTER TABLE {tbl} NO FORCE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {tbl} DISABLE ROW LEVEL SECURITY")

    op.execute("DROP TABLE IF EXISTS password_reset_tokens")
    op.execute("DROP TABLE IF EXISTS refresh_tokens")

    op.execute("ALTER TABLE account_user DROP CONSTRAINT IF EXISTS chk_admin_account")
    op.execute(
        "ALTER TABLE account_user "
        "ALTER COLUMN role TYPE TEXT USING role::text, "
        "ALTER COLUMN role DROP NOT NULL, "
        "ALTER COLUMN role DROP DEFAULT"
    )
    op.execute("ALTER TABLE account_user DROP COLUMN IF EXISTS last_login_at")
    # Suppression des admins (account_id NULL) avant restauration NOT NULL.
    # Les FK audit_log.user_id -> account_user.id doivent d'abord être nettoyées.
    op.execute(
        "DELETE FROM audit_log WHERE user_id IN "
        "(SELECT id FROM account_user WHERE account_id IS NULL)"
    )
    op.execute("DELETE FROM account_user WHERE account_id IS NULL")
    op.execute("ALTER TABLE account_user ALTER COLUMN account_id SET NOT NULL")
    op.execute("DROP TYPE IF EXISTS account_user_role")
    # Les rôles SQL ne sont pas supprimés (peuvent être utilisés ailleurs).
