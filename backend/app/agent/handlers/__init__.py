"""F55 — Handlers de mutation enregistrés via ``@mutation_handler``.

Ce package héberge les handlers concrets ; les services métier (entreprise,
projets) sont **lus** mais leurs APIs ne sont **pas modifiées** ici (zone
F11/F12 maintenue). Quand le service expose déjà un point d'entrée mutateur
adéquat, on l'appelle simplement.

L'enregistrement est centralisé via ``register_mutation_handlers()`` qui doit
être invoqué au boot APRÈS l'enregistrement des tools dans ``TOOL_REGISTRY``
(F17).
"""

from __future__ import annotations

import logging

from app.agent.handlers import (
    company_profile,
    project_create,
    project_delete,
    project_update,
)

logger = logging.getLogger(__name__)


_REGISTRARS = (
    company_profile.register,
    project_create.register,
    project_update.register,
    project_delete.register,
)


def register_mutation_handlers() -> None:
    """Enregistre tous les handlers F55 livrés (US1, US3 partiels)."""
    for fn in _REGISTRARS:
        fn()


__all__ = ["register_mutation_handlers"]
