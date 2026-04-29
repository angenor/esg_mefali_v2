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


def _build_engine():
    settings = get_settings()
    return create_engine(
        settings.database_url,
        pool_pre_ping=True,
        future=True,
    )


# Engine paresseux : créé à l'import si la config est valide.
engine = _build_engine()
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)


def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI : ouvre une session, la ferme proprement."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
