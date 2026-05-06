"""F57 — Mémoire agent (RAG long terme + entity memory + recall log).

Sous-package responsable de :

- la **recherche cosine pgvector** sur ``chat_message.embedding``
  (``long_term.search_long_term``),
- le **cache embedding par tour** (``embedding_cache.get_or_compute``),
- le **tracing recall** (``recall_log.write_recall_log``),
- la **compaction async** des threads ≥ 100 msgs (``compactors.compact_thread``),
- la **persistance résumée par entité** (``entity_memory.update_entity_memory``),
- l'**enregistrement des hooks post-mutation** auprès du dispatcher F55.

Invariants critiques :

- scope **thread_id + account_id** systématique (P2 RLS + anti-fuite cross-thread),
- **forget RGPD** synchrone, ne touche jamais ``chat_message.content`` (P3),
- **audit log append-only** (``source_of_change='memory_system'``) sur tout write
  mémoire (compaction, entity_memory CRUD, forget RGPD),
- **fallback dégradé** sans crash si Voyage / pgvector indisponible (FR-014).
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)


_HOOK_INSTALLED: bool = False


def install_post_mutation_hook() -> None:
    """Enregistre les hooks post-mutation auprès du dispatcher F55 (F57 / US7).

    Idempotent : appelable plusieurs fois sans effet de bord (un flag interne
    empêche les doublons après la première installation réussie).
    """
    global _HOOK_INSTALLED
    if _HOOK_INSTALLED:
        return
    from app.agent.dispatcher import after_dispatch, before_dispatch
    from app.agent.memory.entity_memory import (
        build_after_dispatch_hook,
        build_before_dispatch_hook,
    )

    before_dispatch(build_before_dispatch_hook())
    after_dispatch(build_after_dispatch_hook())
    _HOOK_INSTALLED = True


def _reset_hook_installed_flag() -> None:
    """Réservé aux tests."""
    global _HOOK_INSTALLED
    _HOOK_INSTALLED = False


__all__ = ["install_post_mutation_hook"]
