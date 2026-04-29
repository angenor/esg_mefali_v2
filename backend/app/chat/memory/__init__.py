"""F18 — Mémoire contextuelle LLM.

Sous-package responsable de :

- la **construction du contexte** injecté au LLM à chaque tour
  (profil entreprise + projets actifs + 15 derniers messages),
- la **compaction** sous budget tokens contrôlé,
- l'extraction d'un texte pertinent pour l'**embedding des messages
  payload tool** (label/title plutôt que JSON brut),
- l'**outil ``recall_history``** (P2) — recherche pgvector intra-thread
  sur les messages plus anciens que les 15 derniers.

Invariants critiques :

- pas de cache profil/projets entre tours (FR-009),
- aucune fuite de champs sensibles (FR-014, deny-by-default),
- isolation par compte (RLS) sur ``recall_history`` (FR-015),
- gating ``recall_history`` au-dessus de 15 messages dans le thread (FR-011).
"""

from __future__ import annotations

from app.chat.memory.compactors import (
    DEFAULT_DESC_LIMIT,
    DEFAULT_MAX_PROJECTS,
    PROFILE_ALLOWED_KEYS,
    PROJECT_ACTIVE_DENYLIST,
    PROJECT_ALLOWED_KEYS,
    compact_profile,
    compact_projets,
    estimate_tokens,
    extract_embedding_text,
    fit_to_budget,
)
from app.chat.memory.context_builder import (
    ChatMessageView,
    ContextBundle,
    build_context,
    render_bundle,
)
from app.chat.memory.recall_history_tool import (
    RecallHistoryArgs,
    RecallHit,
    execute_recall_history,
)

__all__ = [
    "DEFAULT_DESC_LIMIT",
    "DEFAULT_MAX_PROJECTS",
    "PROFILE_ALLOWED_KEYS",
    "PROJECT_ACTIVE_DENYLIST",
    "PROJECT_ALLOWED_KEYS",
    "ChatMessageView",
    "ContextBundle",
    "RecallHistoryArgs",
    "RecallHit",
    "build_context",
    "compact_profile",
    "compact_projets",
    "estimate_tokens",
    "execute_recall_history",
    "extract_embedding_text",
    "fit_to_budget",
    "render_bundle",
]
