"""Tests fail-fast de la configuration (T013)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError


def test_get_settings_loads_from_env(clean_settings_cache):
    """Smoke test : la config se charge si toutes les vars sont là."""
    from app.config import get_settings

    s = get_settings()
    assert s.LLM_MODEL  # non vide
    assert s.DB_PASSWORD  # non vide
    assert s.database_url.startswith("postgresql+psycopg://")


def test_missing_db_password_raises_validation_error(
    clean_settings_cache, isolate_env, tmp_path
):
    """T013 — pop DB_PASSWORD → ValidationError."""
    isolate_env.delenv("DB_PASSWORD", raising=False)
    # Empêche pydantic-settings de recharger DB_PASSWORD depuis le .env du repo.
    isolate_env.chdir(tmp_path)

    from app import config as cfg_module

    with pytest.raises(ValidationError):
        # Force l'instanciation sans charger le .env du repo.
        cfg_module.Settings(_env_file=None)  # type: ignore[call-arg]


def test_database_url_format(clean_settings_cache):
    """L'URL SQLAlchemy doit être bien formée."""
    from app.config import get_settings

    url = get_settings().database_url
    assert "@" in url and url.endswith("/esg_mefali")


def test_get_db_yields_session_and_closes(clean_settings_cache):
    """get_db() doit yielder une session SQLAlchemy puis la fermer."""
    from app.db import get_db

    gen = get_db()
    session = next(gen)
    assert session is not None
    # Termine le generator → close() appelé.
    try:
        next(gen)
    except StopIteration:
        pass
