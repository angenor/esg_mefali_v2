"""F50 T007 — Empreinte SHA-256 streaming des contenus uploadés.

Calcul côté serveur ; on ne fait jamais confiance à l'empreinte client seule
pour la sécurité (cf. data-model.md §7).
"""

from __future__ import annotations

import hashlib
from typing import BinaryIO

_CHUNK = 64 * 1024


def sha256_bytes(data: bytes) -> str:
    """Retourne le SHA-256 hex (64 chars) d'un buffer."""
    return hashlib.sha256(data).hexdigest()


def sha256_stream(stream: BinaryIO) -> str:
    """Calcule le SHA-256 hex d'un flux binaire en streaming."""
    h = hashlib.sha256()
    while True:
        chunk = stream.read(_CHUNK)
        if not chunk:
            break
        h.update(chunk)
    return h.hexdigest()


def is_valid_sha256_hex(value: str) -> bool:
    """Vérifie qu'une chaîne est bien un SHA-256 hex (64 chars, [0-9a-f])."""
    if not isinstance(value, str) or len(value) != 64:
        return False
    try:
        int(value, 16)
    except ValueError:
        return False
    return True
