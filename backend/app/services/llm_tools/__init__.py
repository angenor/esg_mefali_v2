"""F03 US2 — Définitions function-calling OpenRouter pour les 3 tools sourçage.

``TOOL_SPECS`` est consommé par F14 (LangGraph) pour publier les tools au LLM
via le paramètre ``tools`` du chat completion.
"""

from __future__ import annotations

from app.services.llm_tools.cite_source import handle_cite_source
from app.services.llm_tools.flag_unsourced import handle_flag_unsourced
from app.services.llm_tools.search_source import handle_search_source

__all__ = [
    "TOOL_SPECS",
    "handle_cite_source",
    "handle_flag_unsourced",
    "handle_search_source",
]


TOOL_SPECS: list[dict] = [
    {
        "type": "function",
        "function": {
            "name": "cite_source",
            "description": (
                "Cite une source vérifiée (renvoie ses métadonnées). Use when: "
                "tu vas affirmer un chiffre, seuil, critère, formule, facteur "
                "d'émission, document requis ou citer un référentiel."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": ["source_id"],
                "properties": {
                    "source_id": {
                        "type": "string",
                        "format": "uuid",
                        "description": "UUID d'une Source au statut verified.",
                    },
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_source",
            "description": (
                "Recherche hybride (full-text + vectoriel) sur le catalogue de "
                "sources verifiées. Use when: tu ne connais pas l'id d'une source."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": ["query"],
                "properties": {
                    "query": {"type": "string", "minLength": 1, "maxLength": 256},
                    "publisher": {"type": "string", "maxLength": 100},
                    "k": {"type": "integer", "minimum": 1, "maximum": 50, "default": 10},
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "flag_unsourced",
            "description": (
                "Journalise une affirmation pour laquelle aucune source vérifiée "
                "n'a été trouvée. Use when: tu choisis de répondre 'pas de source'."
            ),
            "parameters": {
                "type": "object",
                "additionalProperties": False,
                "required": ["claim"],
                "properties": {
                    "claim": {"type": "string", "minLength": 1, "maxLength": 2000},
                    "context": {"type": "object", "additionalProperties": True},
                },
            },
        },
    },
]
