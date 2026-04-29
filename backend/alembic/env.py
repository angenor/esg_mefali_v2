"""Alembic env — utilise app.config.get_settings() pour DATABASE_URL."""

from __future__ import annotations

from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool

from alembic import context
from app.config import get_settings

# Alembic Config object
config = context.config

# Logging conf depuis alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Injecte l'URL depuis Settings (pas de duplication)
config.set_main_option("sqlalchemy.url", get_settings().database_url)

# Pas de metadata SQLAlchemy auto-générée en F01 (les modèles ORM viendront avec F02+).
target_metadata = None


def run_migrations_offline() -> None:
    """Mode offline (génération SQL sans connexion)."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Mode online (connexion réelle)."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
