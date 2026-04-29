-- F02 — Création des rôles SQL pour RLS.
-- Exécuté automatiquement à la première création de la base via docker-entrypoint-initdb.d.
-- Idempotent : DO $$ ... pour vérifier l'existence avant CREATE ROLE.

DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
        CREATE ROLE app_user LOGIN PASSWORD :'app_user_password';
    END IF;

    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'migrator') THEN
        CREATE ROLE migrator LOGIN PASSWORD :'migrator_password' BYPASSRLS;
    END IF;
END
$$;

-- Permissions seront accordées au cours des migrations Alembic.
GRANT USAGE ON SCHEMA public TO app_user;
GRANT USAGE, CREATE ON SCHEMA public TO migrator;
