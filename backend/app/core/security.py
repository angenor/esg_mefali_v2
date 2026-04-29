"""F02 — Helpers de sécurité : bcrypt, JWT, CSRF, opaque tokens, password policy.

T008 — Référence plan.md :
- ``hash_password(plain) -> str`` / ``verify_password(plain, hash) -> bool`` : bcrypt cost 12.
- ``create_access_token`` / ``decode_access_token`` : JWT HS256, signé avec ``JWT_SECRET``.
- ``generate_csrf_token`` / ``verify_csrf_token`` : double-submit, comparaison constante.
- ``generate_opaque_token`` / ``sha256_hex`` : refresh tokens et password-reset tokens.
- ``validate_password_policy`` : ≥12 chars, 1 maj, 1 min, 1 chiffre.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import time
from datetime import UTC, datetime, timedelta
from typing import Any

import bcrypt
from jose import jwt
from jose.exceptions import JWTError

from app.config import get_settings

# bcrypt cost 12 (~250ms sur CPU moderne, alignement OWASP).
BCRYPT_ROUNDS = 12
# bcrypt limite à 72 bytes ; on tronque uniformément (alignement avec Django/passlib).
_BCRYPT_MAX_BYTES = 72

# Algorithme JWT
JWT_ALGORITHM = "HS256"
DEFAULT_ACCESS_TTL_SECONDS = 60 * 60 * 24  # 24h


class InvalidTokenError(Exception):
    """JWT invalide, expiré ou falsifié."""


class PasswordPolicyError(ValueError):
    """Mot de passe ne respecte pas la politique."""


# --------- Password hashing (bcrypt) ---------


def _to_bcrypt_bytes(plain: str) -> bytes:
    """Encode + tronque à 72 bytes (limite bcrypt)."""
    return plain.encode("utf-8")[:_BCRYPT_MAX_BYTES]


def hash_password(plain: str) -> str:
    """Retourne le hash bcrypt du mot de passe en clair."""
    if not isinstance(plain, str):
        raise TypeError("plain doit être str")
    salt = bcrypt.gensalt(rounds=BCRYPT_ROUNDS)
    return bcrypt.hashpw(_to_bcrypt_bytes(plain), salt).decode("ascii")


def verify_password(plain: str, hashed: str) -> bool:
    """Vérifie un mot de passe contre son hash bcrypt. Tolérant aux entrées vides."""
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(_to_bcrypt_bytes(plain), hashed.encode("ascii"))
    except (ValueError, TypeError):
        return False


# --------- JWT (HS256) ---------


def create_access_token(payload: dict[str, Any], ttl_seconds: int = DEFAULT_ACCESS_TTL_SECONDS) -> str:
    """Crée un access JWT HS256.

    Le payload doit a minima contenir ``sub`` (user_id). ``exp`` et ``iat`` sont ajoutés.
    Si ttl_seconds est négatif, le token sera expiré immédiatement (utile pour tests).
    """
    now = datetime.now(UTC)
    body = dict(payload)
    body["iat"] = int(now.timestamp())
    body["exp"] = int((now + timedelta(seconds=ttl_seconds)).timestamp())
    secret = get_settings().JWT_SECRET
    return jwt.encode(body, secret, algorithm=JWT_ALGORITHM)


def decode_access_token(token: str) -> dict[str, Any]:
    """Décode un JWT HS256 et vérifie sa signature + expiration.

    Lève ``InvalidTokenError`` en cas d'échec.
    """
    secret = get_settings().JWT_SECRET
    try:
        return jwt.decode(token, secret, algorithms=[JWT_ALGORITHM])
    except JWTError as exc:
        raise InvalidTokenError(str(exc)) from exc


# --------- CSRF (double-submit, comparaison constante) ---------


def generate_csrf_token(n_bytes: int = 32) -> str:
    """Génère un token CSRF URL-safe."""
    return secrets.token_urlsafe(n_bytes)


def verify_csrf_token(submitted: str, cookie_value: str) -> bool:
    """Comparaison constante du token soumis (header) vs cookie."""
    if not submitted or not cookie_value:
        return False
    return hmac.compare_digest(submitted, cookie_value)


# --------- Opaque tokens + SHA-256 ---------


def generate_opaque_token(n_bytes: int = 32) -> str:
    """Génère un token opaque URL-safe pour refresh / password-reset."""
    return secrets.token_urlsafe(n_bytes)


def sha256_hex(token: str) -> str:
    """Hex SHA-256 d'une chaîne (pour stocker un token sans le clair)."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


# --------- Password policy ---------

PASSWORD_MIN_LENGTH = 12
PASSWORD_MAX_LENGTH = 128


def validate_password_policy(password: str) -> None:
    """Vérifie la politique de mot de passe. Lève ``PasswordPolicyError`` sinon.

    Règles :
    - Longueur entre 12 et 128 caractères.
    - Au moins une majuscule, une minuscule et un chiffre.
    """
    if not isinstance(password, str) or len(password) < PASSWORD_MIN_LENGTH:
        raise PasswordPolicyError(
            f"Le mot de passe doit comporter au moins {PASSWORD_MIN_LENGTH} caractères."
        )
    if len(password) > PASSWORD_MAX_LENGTH:
        raise PasswordPolicyError(
            f"Le mot de passe ne doit pas dépasser {PASSWORD_MAX_LENGTH} caractères."
        )
    if not any(c.isupper() for c in password):
        raise PasswordPolicyError("Le mot de passe doit contenir au moins une majuscule.")
    if not any(c.islower() for c in password):
        raise PasswordPolicyError("Le mot de passe doit contenir au moins une minuscule.")
    if not any(c.isdigit() for c in password):
        raise PasswordPolicyError("Le mot de passe doit contenir au moins un chiffre.")


__all__ = [
    "DEFAULT_ACCESS_TTL_SECONDS",
    "InvalidTokenError",
    "JWT_ALGORITHM",
    "PASSWORD_MAX_LENGTH",
    "PASSWORD_MIN_LENGTH",
    "PasswordPolicyError",
    "create_access_token",
    "decode_access_token",
    "generate_csrf_token",
    "generate_opaque_token",
    "hash_password",
    "sha256_hex",
    "validate_password_policy",
    "verify_csrf_token",
    "verify_password",
    "time",  # used elsewhere
]
