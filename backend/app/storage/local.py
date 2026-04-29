"""F12 - LocalStorage : implementation filesystem locale du Protocol Storage."""

from __future__ import annotations

import os
from pathlib import Path
from typing import BinaryIO


class LocalStorage:
    """Persiste les fichiers sous `root_dir`. Cree les sous-dossiers a la volee."""

    def __init__(self, root_dir: str | Path) -> None:
        self.root_dir = Path(root_dir).resolve()
        self.root_dir.mkdir(parents=True, exist_ok=True)

    def _abs(self, rel_path: str) -> Path:
        # Empeche escape via "../" (path traversal).
        rel = Path(rel_path).as_posix()
        if rel.startswith("/") or ".." in Path(rel_path).parts:
            raise ValueError(f"Invalid relative path: {rel_path}")
        return (self.root_dir / rel_path).resolve()

    def save(self, rel_path: str, data: bytes | BinaryIO) -> str:
        abs_path = self._abs(rel_path)
        # Securise : abs_path doit rester sous root_dir.
        if not str(abs_path).startswith(str(self.root_dir) + os.sep) and abs_path != self.root_dir:
            raise ValueError(f"Path escapes root_dir: {rel_path}")
        abs_path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(data, (bytes, bytearray)):
            abs_path.write_bytes(bytes(data))
        else:
            with open(abs_path, "wb") as fh:
                while True:
                    chunk = data.read(64 * 1024)
                    if not chunk:
                        break
                    fh.write(chunk)
        return str(abs_path)

    def read(self, rel_path: str) -> bytes:
        return self._abs(rel_path).read_bytes()

    def delete(self, rel_path: str) -> None:
        p = self._abs(rel_path)
        if p.exists():
            p.unlink()

    def exists(self, rel_path: str) -> bool:
        return self._abs(rel_path).exists()
