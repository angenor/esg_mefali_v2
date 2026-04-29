"""F19 — Snapshot version : interface no-op (persistence reportée à F20).

Fournit un point d'entrée stable pour figer la version d'une skill au démarrage
d'une conversation (US8). En MVP F19, log uniquement — la table ``thread_skill``
sera ajoutée par F20 quand le CRUD admin sera livré.
"""

from __future__ import annotations

import logging
import uuid
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SkillSnapshot:
    """Identifiant immuable d'une snapshot version."""

    thread_id: uuid.UUID
    skill_id: uuid.UUID
    version: int


def snapshot_skill_version(
    thread_id: uuid.UUID | str,
    skill_id: uuid.UUID | str,
    version: int,
) -> SkillSnapshot:
    """Fige la version d'une skill pour un thread donné (interface MVP).

    En F19 : log uniquement. La persistence en table ``thread_skill`` est livrée
    par F20. Le retour est un dataclass immuable utilisable côté appelant.
    """
    if not isinstance(thread_id, uuid.UUID):
        thread_id = uuid.UUID(str(thread_id))
    if not isinstance(skill_id, uuid.UUID):
        skill_id = uuid.UUID(str(skill_id))
    if version < 1:
        raise ValueError("version must be >= 1")

    snapshot = SkillSnapshot(
        thread_id=thread_id, skill_id=skill_id, version=version
    )
    logger.info(
        "skill.snapshot thread=%s skill=%s version=%s",
        thread_id,
        skill_id,
        version,
    )
    return snapshot


__all__ = ["SkillSnapshot", "snapshot_skill_version"]
