"""F54 / FR-015 — Hash SHA-256 du system prompt construit (US7).

Persisté dans ``agent_run.system_prompt_hash`` à la fin de chaque tour.
Permet de rejouer un comportement passé (audit, debug) en s'assurant que
deux runs ayant le même hash ont eu rigoureusement le même prompt.
"""

from __future__ import annotations

import hashlib


def compute_prompt_hash(prompt: str) -> str:
    """Renvoie le SHA-256 hexadécimal de ``prompt`` (64 caractères).

    L'encodage UTF-8 est utilisé. ``prompt == ""`` renvoie le hash de la
    chaîne vide (cohérent et déterministe).
    """
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()


__all__ = ["compute_prompt_hash"]
