"""F54 / FR-013 — Anti-injection des champs string PME.

Avant insertion dans le system prompt (qui peut être passé à un mécanisme de
templating en aval ou échappé par un éval LLM), on neutralise systématiquement
les caractères ``{`` et ``}`` (collisionnent avec f-strings et avec la syntaxe
Jinja ``{% ... %}`` / ``{{ ... }}``), et on tronque chaque champ à
:data:`MAX_FIELD_LEN` caractères pour éviter qu'un champ surdimensionné ne
phagocyte le budget tokens.

Pattern unique : :func:`clean_user_str` (None-safe).

Tous les fields user-controlled (raison sociale, description projet, libellé
indicateur, etc.) doivent transiter par ce module avant d'entrer dans une
dataclass de :mod:`app.agent.context.models`.
"""

from __future__ import annotations

#: Longueur maximale d'un champ string user-controlled inséré dans un prompt.
MAX_FIELD_LEN: int = 500


def escape_template_chars(s: str) -> str:
    """Double ``{`` et ``}`` pour neutraliser f-strings et templates Jinja.

    Idempotent défensif : ``{{`` redevient ``{{{{`` (sécurité au sens large).
    Le builder F54 n'évalue jamais ce résultat comme f-string : c'est une
    précaution pour le cas où un futur consommateur (ex. un ``str.format``
    accidentel) traite le prompt comme un template.
    """
    return s.replace("{", "{{").replace("}", "}}")


def truncate_field(s: str, max_len: int = MAX_FIELD_LEN) -> str:
    """Tronque ``s`` à ``max_len`` et ajoute ``…`` si troncature nécessaire.

    L'ellipsis fait partie du quota : la longueur de sortie est garantie
    ``<= max_len``.
    """
    if len(s) <= max_len:
        return s
    if max_len <= 0:
        return ""
    # Réserver 1 caractère pour ``…`` (compté dans max_len).
    return s[: max_len - 1] + "…"


def clean_user_str(s: str | None, max_len: int = MAX_FIELD_LEN) -> str:
    """Pipeline complet : ``None → ''`` puis :func:`escape_template_chars`
    puis :func:`truncate_field`.

    L'ordre est important :
    1. ``None``-safety (renvoie ``''``).
    2. Escape **avant** troncature pour éviter qu'une coupure ne casse un
       ``{{`` en deux moitiés (ex. ``{{`` → ``{`` malformé).
    """
    if s is None:
        return ""
    return truncate_field(escape_template_chars(s), max_len=max_len)


__all__ = [
    "MAX_FIELD_LEN",
    "clean_user_str",
    "escape_template_chars",
    "truncate_field",
]
