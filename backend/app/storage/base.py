"""F12 - Storage Protocol abstraction.

Permet de swapper le stockage local vers MinIO/S3 sans changer les services.
"""

from __future__ import annotations

from typing import BinaryIO, Protocol


class Storage(Protocol):
    """Interface generique de stockage de fichiers binaires."""

    def save(self, rel_path: str, data: bytes | BinaryIO) -> str:
        """Persiste les bytes a `rel_path` (chemin relatif). Retourne le chemin absolu/uri."""

    def read(self, rel_path: str) -> bytes:
        """Lit les bytes depuis `rel_path`."""

    def delete(self, rel_path: str) -> None:
        """Supprime le fichier a `rel_path` (idempotent)."""

    def exists(self, rel_path: str) -> bool:
        """Retourne True si le fichier existe."""
