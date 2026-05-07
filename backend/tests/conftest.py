"""Fixtures pytest partagées."""

from __future__ import annotations

import os
from collections.abc import Generator

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine


def _db_reachable() -> bool:
    """Tente une connexion rapide à Postgres ; renvoie False si KO."""
    try:
        from app.config import get_settings

        engine = create_engine(get_settings().database_url, pool_pre_ping=False)
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        engine.dispose()
        return True
    except Exception:
        return False


DB_AVAILABLE = _db_reachable()

requires_db = pytest.mark.skipif(
    not DB_AVAILABLE,
    reason="Postgres indisponible — démarrer `docker compose up -d postgres`.",
)


@pytest.fixture(scope="session")
def db_engine() -> Generator[Engine, None, None]:
    """Engine SQLAlchemy de test (réutilise la DB principale)."""
    from app.config import get_settings

    engine = create_engine(get_settings().database_url, pool_pre_ping=True)
    yield engine
    engine.dispose()


@pytest.fixture()
def clean_settings_cache():
    """Vide le cache lru_cache de get_settings() pour les tests de config."""
    from app.config import get_settings

    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture()
def isolate_env(monkeypatch):
    """Donne au test la possibilité de modifier os.environ et restore."""
    # monkeypatch gère déjà le restore.
    yield monkeypatch


def pytest_configure(config):
    # Désactive complètement le chargement du fichier .env pour les tests
    # qui patchent l'env (sinon pydantic-settings recharge depuis disque).
    os.environ.setdefault("PYTEST_RUNNING", "1")
    # F53 — register tools side-effect early to avoid test pollution between
    # tests that depend on TOOL_REGISTRY (skills validation utilise
    # ``respond_user`` qui n'est PAS dans le registre F14, donc on AJOUTE
    # ``respond_user`` au registre côté tests pour rester compat).
    try:
        from pydantic import BaseModel, ConfigDict

        from app.agent.state import ToolCategory
        from app.orchestrator.tool_registry import TOOL_REGISTRY, tool

        if "respond_user" not in TOOL_REGISTRY:
            class _RespondUserPayload(BaseModel):
                model_config = ConfigDict(extra="forbid")
                text: str = ""

            # category=READ : pas de mutation DB → pas besoin de handler
            # ``MUTATION_HANDLERS`` au boot (évite ``HandlerRegistrationError``
            # logué en ERROR au lifespan).
            tool(
                name="respond_user",
                description="Réponse texte simple",
                use_when="Aucun tool structuré n'est nécessaire",
                dont_use_when="Une mutation/visu est attendue",
                schema=_RespondUserPayload,
                category=ToolCategory.READ,
            )
    except Exception:  # noqa: BLE001 - never break tests collection
        pass


# ---------------------------------------------------------------------------
# F53 — Agent fixtures (importées depuis tests.agent_fixtures)
# ---------------------------------------------------------------------------
# pytest les détecte via la ré-exportation explicite ci-dessous.
from tests.agent_fixtures import (  # noqa: E402, F401  -- pytest collecte
    FakeLLM,
    fake_llm_factory,
    make_text_response,
    make_tool_call_response,
)
