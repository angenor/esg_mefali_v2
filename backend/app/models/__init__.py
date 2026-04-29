"""F02 — Modèles SQLAlchemy ORM (déclaratifs).

Ces modèles sont volontairement minimaux : ils mappent uniquement les colonnes
nécessaires à la logique d'auth. Le reste des tables F01 reste manipulé en SQL
brut via Alembic.
"""

from __future__ import annotations

from sqlalchemy.orm import DeclarativeBase


class Base(DeclarativeBase):
    """Base déclarative SQLAlchemy partagée."""


from app.models.account import Account  # noqa: E402,F401
from app.models.account_user import AccountUser  # noqa: E402,F401
from app.models.password_reset_token import PasswordResetToken  # noqa: E402,F401
from app.models.refresh_token import RefreshToken  # noqa: E402,F401

__all__ = [
    "Account",
    "AccountUser",
    "Base",
    "PasswordResetToken",
    "RefreshToken",
]
