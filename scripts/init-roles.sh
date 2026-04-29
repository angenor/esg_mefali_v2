#!/usr/bin/env bash
# F02 — Création des rôles SQL au démarrage du container Postgres.
# Monté comme /docker-entrypoint-initdb.d/init-roles.sh dans docker-compose.yml.
# Variables d'env attendues : APP_USER_PASSWORD, MIGRATOR_PASSWORD.
# Idempotent.
set -e

: "${APP_USER_PASSWORD:?APP_USER_PASSWORD must be set}"
: "${MIGRATOR_PASSWORD:?MIGRATOR_PASSWORD must be set}"

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    DO \$\$
    BEGIN
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'app_user') THEN
            CREATE ROLE app_user LOGIN PASSWORD '${APP_USER_PASSWORD}';
        END IF;
        IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'migrator') THEN
            CREATE ROLE migrator LOGIN PASSWORD '${MIGRATOR_PASSWORD}' BYPASSRLS;
        END IF;
    END
    \$\$;

    GRANT USAGE ON SCHEMA public TO app_user;
    GRANT USAGE, CREATE ON SCHEMA public TO migrator;
EOSQL
