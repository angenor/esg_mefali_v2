"""Configuration centralisée — fail-fast au boot.

Charge les variables depuis `.env` (racine du repo) via pydantic-settings.
Toute variable obligatoire manquante déclenche une `ValidationError` au démarrage.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# .env est à la racine du repo (un cran au-dessus de backend/)
_REPO_ROOT = Path(__file__).resolve().parents[2]
_ENV_FILE = _REPO_ROOT / ".env"

# Expose .env values to os.environ so legacy modules reading os.environ
# directly (e.g. app/attestations/crypto.py) see the same values.
load_dotenv(_ENV_FILE, override=False)


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

    # --- Auth (F02) ---
    JWT_SECRET: str = Field(..., min_length=1)
    CSRF_SECRET: str = "csrf-default-change-me"
    COOKIE_DOMAIN: str = "localhost"
    COOKIE_SECURE: bool = False
    APP_USER_PASSWORD: str = ""
    MIGRATOR_PASSWORD: str = ""

    # --- Email (F02) ---
    EMAIL_BACKEND: str = "console"
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    RESET_PASSWORD_BASE_URL: str = "http://localhost:3000/reset-password"
    PASSWORD_RESET_TTL_MINUTES: int = 60

    # --- Embeddings (utilisé en F18) ---
    VOYAGE_API_KEY: str = Field(..., min_length=1)

    # --- Speech-to-text (utilisé en F22) ---
    REPLICATE_API_TOKEN: str = Field(..., min_length=1)

    # --- F24 (rapport conformité PDF) ---
    RAPPORT_STORAGE_DIR: str = "var/rapports"

    # --- F05 (data privacy & FX) ---
    EXCHANGERATE_API_KEY: str = ""
    PURGE_PSEUDONYM_PEPPER: str = ""
    FX_DEFAULT_DISPLAY_CURRENCY: str = "XOF"
    FX_STALE_ALERT_DAYS: int = 7

    # --- F53 (Agent LangGraph) ---
    # Mode : `langgraph` (défaut, agent activé) ou `raw` (proxy LLM F13).
    LLM_AGENT_MODE: Literal["langgraph", "raw"] = "langgraph"
    # Nombre max de tools exposés au LLM par tour (P9, FR-015).
    LLM_AGENT_MAX_TOOLS: int = Field(default=10, ge=1, le=50)
    # Retries Pydantic max avant fallback texte (FR-006).
    LLM_AGENT_MAX_RETRIES: int = Field(default=2, ge=0, le=10)
    # Timeout LLM par tour en secondes (Q3 clarification).
    LLM_AGENT_TIMEOUT_S: float = Field(default=30.0, gt=0.0)
    # Mode de tracing : off, db, db+stdout (FR-015).
    LLM_AGENT_TRACE: Literal["off", "db", "db+stdout"] = "db"
    # Compatibilité OpenAI clients pour HEAD /v1/models (healthcheck).
    LLM_HEALTH_TIMEOUT_S: float = Field(default=1.0, gt=0.0)

    # --- F54 (Agent Context Builder) ---
    # Budget de tokens pour le system prompt dynamique (NFR-002, FR-011).
    LLM_AGENT_PROMPT_BUDGET_TOKENS: int = Field(default=4000, ge=512, le=64000)
    # Encoding tiktoken utilisé pour ``count_tokens`` (FR-005, FR-011).
    LLM_TIKTOKEN_ENCODING: str = Field(default="cl100k_base", min_length=1)

    # --- F55 (Agent Tool Dispatch & SSE Bridge) ---
    # Backend du rate limiter : ``memory`` (dev) ou ``redis`` (prod).
    LLM_AGENT_RATE_LIMIT_BACKEND: Literal["memory", "redis"] = "memory"
    # Budget de tokens pour la sérialisation des résultats READ (FR-015).
    LLM_AGENT_READ_BUDGET_TOKENS: int = Field(default=1500, ge=128, le=64000)
    # TTL applicatif d'une confirmation user (FR-012, US3).
    LLM_AGENT_CONFIRMATION_TTL_SECONDS: int = Field(default=180, ge=30, le=3600)
    # Header HTTP utilisé par les admins pour activer le mode dry_run (US6).
    LLM_AGENT_DRY_RUN_HEADER: str = Field(default="X-Agent-DryRun", min_length=1)

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
