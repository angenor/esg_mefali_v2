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
from app.agent.handlers import (
    flag_unsourced as _flag_unsourced_module,
)

logger = logging.getLogger(__name__)


_REGISTRARS = (
    company_profile.register,
    project_create.register,
    project_update.register,
    project_delete.register,
    _flag_unsourced_module.register,
)


def register_mutation_handlers() -> None:
    """Enregistre tous les handlers F55 + F56 livrés."""
    for fn in _REGISTRARS:
        fn()


def register_reinvoke_sourcing_handlers() -> None:
    """F56 — Enregistre les handlers READ ``cite_source`` / ``search_source``
    dans ``app.agent.nodes.dispatch_tool._REINVOKE_HANDLERS``.

    Idempotent : ré-import safe.
    """
    from app.agent.handlers.cite_source import cite_source_handler
    from app.agent.handlers.search_source import search_source_handler
    from app.agent.nodes.dispatch_tool import _REINVOKE_HANDLERS

    _REINVOKE_HANDLERS.setdefault("cite_source", cite_source_handler)
    _REINVOKE_HANDLERS.setdefault("search_source", search_source_handler)


def register_reinvoke_memory_handlers() -> None:
    """F57 — Enregistre le handler READ ``recall_history``.

    Idempotent : ré-import safe (utilise ``setdefault``).
    """
    from app.agent.handlers import recall_history as _recall_history_module

    _recall_history_module.register()


__all__ = [
    "register_mutation_handlers",
    "register_reinvoke_memory_handlers",
    "register_reinvoke_sourcing_handlers",
]
