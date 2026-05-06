"""F56 — Enregistrement des 3 sourcing tools dans ``TOOL_REGISTRY``.

Lazy registration : le module enregistre au premier import. Idempotent
(skip silencieux si déjà présent — utile en tests).

Caller : ``app.main`` (boot) appelle ``register_sourcing_tools`` ; les tests
peuvent aussi importer le module directement (auto-register).
"""

from __future__ import annotations

from app.agent.sourcing.tool_schemas import (
    CiteSourceArgs,
    FlagUnsourcedArgs,
    SearchSourceArgs,
)
from app.agent.state import ToolCategory
from app.orchestrator.tool_registry import TOOL_REGISTRY, tool


def register_sourcing_tools() -> None:
    """Enregistre les 3 sourcing tools (idempotent)."""
    if "cite_source" not in TOOL_REGISTRY:
        tool(
            name="cite_source",
            description=(
                "Cite une source vérifiée du catalogue ESG Mefali en "
                "fournissant son ``source_id``. Le handler valide que la "
                "source existe ET qu'elle est ``verification_status='verified'`` "
                "avant d'enregistrer la citation."
            ),
            use_when=(
                "Tu introduis une affirmation factuelle (chiffre, seuil, "
                "formule, facteur d'émission, document requis, mot-clé "
                "référentiel) et tu connais déjà le ``source_id`` (ou tu "
                "viens de l'obtenir via ``search_source``)."
            ),
            dont_use_when=(
                "L'affirmation est générique-pédagogique ('En général, "
                "les PME...'). Tu ne connais pas le ``source_id`` (utilise "
                "``search_source`` d'abord). La source est non vérifiée "
                "(utilise ``flag_unsourced``)."
            ),
            schema=CiteSourceArgs,
            category=ToolCategory.READ,
            requires_confirmation=False,
        )

    if "search_source" not in TOOL_REGISTRY:
        tool(
            name="search_source",
            description=(
                "Recherche jusqu'à ``limit`` sources vérifiées par "
                "similarité sémantique (embedding Voyage + pgvector "
                "cosine). En cas d'indisponibilité Voyage, fallback ILIKE "
                "sur title/section/publisher avec ``degraded=true``."
            ),
            use_when=(
                "Tu veux trouver une source vérifiée matchant un sujet "
                "(ex. 'seuil GCF PME', 'facteur émission diesel ADEME') "
                "et tu ne connais pas le ``source_id``."
            ),
            dont_use_when=(
                "Tu connais déjà le ``source_id`` (utilise ``cite_source`` "
                "directement). La query est trop générique ('ESG'). "
                "Sois spécifique."
            ),
            schema=SearchSourceArgs,
            category=ToolCategory.READ,
            requires_confirmation=False,
        )

    if "flag_unsourced" not in TOOL_REGISTRY:
        tool(
            name="flag_unsourced",
            description=(
                "Signale qu'une affirmation factuelle ne peut pas être "
                "sourcée par le catalogue ESG Mefali. Insère une ligne "
                "dans ``unsourced_flag`` (RLS account-scoped) et émet un "
                "event SSE ``unsourced_claim`` ; alimente le backlog admin."
            ),
            use_when=(
                "Tu vas affirmer un chiffre / seuil / délai mais aucune "
                "source vérifiée n'existe en catalogue. Tu préfères être "
                "transparent que d'halluciner."
            ),
            dont_use_when=(
                "Tu peux citer une source (utilise ``cite_source``). "
                "L'affirmation est générique-pédagogique (whitelist). "
                "Le chiffre vient d'un tool DB (déjà ``from_tool=true``)."
            ),
            schema=FlagUnsourcedArgs,
            category=ToolCategory.MUTATION,
            requires_confirmation=False,
        )


# Auto-register au premier import (compat tests).
register_sourcing_tools()


__all__ = ["register_sourcing_tools"]
