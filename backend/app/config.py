"""Configuration centralisée — fail-fast au boot.

Charge les variables depuis `.env` (racine du repo) via pydantic-settings.
Toute variable obligatoire manquante déclenche une `ValidationError` au démarrage.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env est à la racine du repo (un cran au-dessus de backend/)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"


class Settings(BaseSettings):
    """Settings applicatifs — lus depuis l'environnement et `.env`."""

    model_config = SettingsConfigDict(
        env_file=str(_ENV_FILE),
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )

    # --- Postgres (DB_PASSWORD obligatoire) ---
    DB_PASSWORD: str = Field(..., min_length=1)
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = "esg_mefali"
    POSTGRES_USER: str = "esg"

    # --- LLM (sans appel en F01) ---
    LLM_BASE_URL: str = Field(..., min_length=1)
    LLM_API_KEY: str = Field(..., min_length=1)
    LLM_MODEL: str = Field(..., min_length=1)

    # --- Identification application ---
    APP_URL: str = Field(..., min_length=1)

    # --- Auth (utilisé en F02) ---
    JWT_SECRET: str = Field(..., min_length=1)

    # --- Embeddings (utilisé en F18) ---
    VOYAGE_API_KEY: str = Field(..., min_length=1)

    # --- Speech-to-text (utilisé en F22) ---
    REPLICATE_API_TOKEN: str = Field(..., min_length=1)

    @property
    def database_url(self) -> str:
        """URL SQLAlchemy/psycopg pour PostgreSQL."""
        return (
            f"postgresql+psycopg://{self.POSTGRES_USER}:{self.DB_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Retourne l'instance singleton de Settings (cache LRU)."""
    return Settings()  # type: ignore[call-arg]
