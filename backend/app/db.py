"""Database engine + session factory + dépendance FastAPI `get_db()`.

Pattern Money documenté ici (F27/F29 utiliseront ces conventions) :

- Chaque champ monétaire est stocké comme deux colonnes :
  ``<champ>_amount NUMERIC(18,2) NULL`` + ``<champ>_currency CHAR(3) NULL``
- CHECK : ``(amount IS NULL AND currency IS NULL) OR
  (amount IS NOT NULL AND currency IS NOT NULL AND char_length(currency)=3)``
- Devise par défaut pour les seeds : ``XOF`` (FCFA)
- Peg fixe FCFA-EUR : ``FX_PEG_XOF_EUR = Decimal("655.957")`` (UEMOA)
"""

from __future__ import annotations

from collections.abc import Generator
from decimal import Decimal

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from app.config import get_settings

# Constantes Money — usage F27 (simulateur financement) / F29 (credit-scoring).
FX_PEG_XOF_EUR: Decimal = Decimal("655.957")
DEFAULT_CURRENCY: str = "XOF"


def _build_engine(url: str | None = None):
    settings = get_settings()
    return create_engine(
        url or settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


def _build_app_engine():
    """Engine pour l'API : utilise le rôle ``app_user`` (RLS appliquée).

    Si ``APP_USER_PASSWORD`` n'est pas défini, retombe sur l'engine principal
    (utile en dev avant que les rôles aient été créés ou pour les tests).
    """
    settings = get_settings()
    pwd = getattr(settings, "APP_USER_PASSWORD", "")
    if not pwd:
        return _build_engine()
    url = (
        f"postgresql+psycopg://app_user:{pwd}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
    return _build_engine(url)


def _build_migrator_engine():
    """Engine pour Alembic : utilise le rôle ``migrator`` (BYPASS RLS)."""
    settings = get_settings()
    pwd = getattr(settings, "MIGRATOR_PASSWORD", "")
    if not pwd:
        return _build_engine()
    url = (
        f"postgresql+psycopg://migrator:{pwd}"
        f"@{settings.POSTGRES_HOST}:{settings.POSTGRES_PORT}/{settings.POSTGRES_DB}"
    )
    return _build_engine(url)


# Engine paresseux : créé à l'import si la config est valide.
# `engine` reste l'alias historique (rôle propriétaire de la base) ; `engine_app`
# est l'engine `app_user` réellement utilisé par l'API.
engine = _build_engine()
engine_app = _build_app_engine()
SessionLocal = sessionmaker(
    bind=engine_app, autoflush=False, autocommit=False, future=True
)

_engine_migrator = None


def get_engine_migrator():
    """Retourne l'engine ``migrator`` (BYPASS RLS), créé à la demande."""
    global _engine_migrator
    if _engine_migrator is None:
        _engine_migrator = _build_migrator_engine()
    return _engine_migrator


def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI : ouvre une session, la ferme proprement."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
