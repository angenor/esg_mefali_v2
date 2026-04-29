"""Pseudonymisation déterministe pour RTBF (F05 — US1).

Génère un identifiant pseudonyme stable à partir d'un UUID de compte et d'un
pepper applicatif (variable d'environnement `PURGE_PSEUDONYM_PEPPER`, hex 64).
Utilisé par le trigger `audit_log_immutable` lors d'une purge RGPD pour
remplacer `user_id` dans les lignes d'audit existantes — exception strictement
encadrée à l'invariant "audit append-only".
"""

from __future__ import annotations

import hmac
from hashlib import sha256
from uuid import UUID

from app.config import get_settings


class PseudonymPepperMissingError(RuntimeError):
    """Pepper de pseudonymisation absent — boot/purge doit échouer."""


def pseudonymize(account_id: UUID) -> str:
    """Retourne `anon_<hex16>` dérivé de `HMAC-SHA256(uuid.bytes, pepper)`.

    Lève `PseudonymPepperMissingError` si la variable n'est pas configurée.
    """
    settings = get_settings()
    pepper_hex = getattr(settings, "PURGE_PSEUDONYM_PEPPER", "")
    if not pepper_hex:
        raise PseudonymPepperMissingError(
            "PURGE_PSEUDONYM_PEPPER absent — purge RGPD impossible."
        )
    try:
        pepper_bytes = bytes.fromhex(pepper_hex)
    except ValueError as exc:
        raise PseudonymPepperMissingError(
            "PURGE_PSEUDONYM_PEPPER doit être un hex valide (64 chars)."
        ) from exc
    if len(pepper_bytes) != 32:
        raise PseudonymPepperMissingError(
            "PURGE_PSEUDONYM_PEPPER doit faire 32 octets (hex 64 chars)."
        )
    digest = hmac.new(pepper_bytes, account_id.bytes, sha256).hexdigest()
    return f"anon_{digest[:16]}"
