"""F54 / FR-018 — Mode "support admin" (US6).

Quand l'utilisateur courant a ``role == 'admin'``, le builder injecte un
bandeau dédié dans le prompt et marque les tools de mutation comme
``requires_confirmation``.

Sécurité (P7) : il n'existe que deux rôles, ``pme`` et ``admin``.
Ce module ne crée aucun rôle nouveau.
"""

from __future__ import annotations

from collections.abc import Iterable
from uuid import UUID

from app.agent.context.escape import clean_user_str
from app.agent.context.models import ToolRender

_MUTATION_PREFIXES: tuple[str, ...] = (
    "create_",
    "update_",
    "delete_",
    "patch_",
    "submit_",
    "soumettre_",
    "set_",
    "archive_",
)


def render_admin_banner(account_id: UUID | None) -> str:
    """Construit le bandeau "mode support admin" (FR-018).

    Le bandeau cite l'``account_id`` ciblé (ou "compte non spécifié" si
    ``None``) et rappelle la règle "lecture autorisée, mutation sur
    confirmation explicite".
    """
    aid_str = clean_user_str(str(account_id)) if account_id else "compte non spécifié"
    return (
        "# MODE SUPPORT ADMIN\n"
        f"Tu opères en mode support admin pour l'account `{aid_str}`.\n"
        "- Lecture : autorisée.\n"
        "- Mutation : autorisée uniquement après confirmation explicite de "
        "l'utilisateur (ex. « Confirmez-vous la modification ? »).\n"
        "- Toute mutation est journalisée dans l'audit append-only avec "
        "`source_of_change=admin_support` (P3).\n"
        "- Tu n'agis jamais sur un autre `account_id` que celui ci-dessus."
    )


def is_mutation_tool_name(name: str) -> bool:
    """Heuristique pure : un tool est mutation si son nom commence par
    ``create_``, ``update_``, ``delete_``, ``patch_``, ``submit_``, etc."""
    n = name.lower()
    return any(n.startswith(p) for p in _MUTATION_PREFIXES)


def mark_mutation_tools_require_confirmation(
    tools: Iterable[ToolRender],
) -> list[ToolRender]:
    """Annote chaque tool de mutation : ``use_when`` se voit ajouter une
    note explicite ``[requires_confirmation]``.

    Les tools non-mutation sont retournés tels quels (instances immuables).
    """
    out: list[ToolRender] = []
    for t in tools:
        if is_mutation_tool_name(t.name):
            new_use_when = t.use_when
            if "[requires_confirmation]" not in new_use_when:
                if new_use_when:
                    new_use_when = f"{new_use_when} [requires_confirmation]"
                else:
                    new_use_when = "[requires_confirmation]"
            out.append(t.model_copy(update={"use_when": new_use_when}))
        else:
            out.append(t)
    return out


__all__ = [
    "is_mutation_tool_name",
    "mark_mutation_tools_require_confirmation",
    "render_admin_banner",
]
