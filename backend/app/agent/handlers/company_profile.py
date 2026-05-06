"""F55 — Handler ``update_company_profile`` (US1).

Appelle ``app.entreprise.service.update_partial(source_of_change=LLM)`` qui
gère déjà l'audit log + publish EventBus côté service. F55 ne re-déclenche
PAS un audit additionnel (sinon on double-loggerait) — l'invariant audit
``source_of_change='llm'`` est satisfait via le service.

L'enrichissement ``tool_call_id`` / ``agent_run_id`` sur la ligne audit reste
en best-effort F56 (le service F11 ne propage pas ces ids ; le rattachement
viendra via le hook ``after_dispatch`` qui peut INSERT une ligne d'audit
spécifique au dispatch_id si besoin).
"""

from __future__ import annotations

from typing import Any

from app.agent.mutation_ctx import MutationCtx
from app.agent.mutation_handlers import mutation_handler
from app.agent.state import MutationResult
from app.audit.schemas import SourceOfChange
from app.entreprise.service import update_partial
from app.orchestrator.tools.mutations.update_company_profile import (
    UpdateCompanyProfilePayload,
)


def _to_snapshot(row: Any) -> dict[str, Any]:
    """Snapshot léger d'un EntrepriseRow (pour le SSE event mutation)."""
    try:
        return {
            "id": str(row.id),
            "version": row.version,
            "name": getattr(row, "name", None),
            "secteur_code": getattr(row, "secteur_code", None),
            "taille_effectifs": getattr(row, "taille_effectifs", None),
        }
    except Exception:
        return {}


@mutation_handler("update_company_profile")
async def handle_update_company_profile(
    args: UpdateCompanyProfilePayload,
    ctx: MutationCtx,
) -> MutationResult:
    """Met à jour des champs du profil entreprise via le service F11."""
    fields_dict = args.fields.model_dump(exclude_none=True)
    if not fields_dict:
        return MutationResult(
            entity_type="entreprise",
            entity_id=ctx.account_id,  # placeholder ; pas de mutation effective
            fields_updated=[],
            snapshot={"updated": False, "reason": "no_fields_provided"},
        )

    if "taille_ca" in fields_dict and isinstance(fields_dict["taille_ca"], dict):
        ca = fields_dict["taille_ca"]
        fields_dict["taille_ca"] = {"amount": ca["amount"], "currency": ca["currency"]}

    row = update_partial(
        ctx.db,
        account_id=ctx.account_id,
        user_id=ctx.user_id,
        expected_version=args.expected_version,
        payload=fields_dict,
        source_of_change=SourceOfChange.LLM,
    )

    return MutationResult(
        entity_type="entreprise",
        entity_id=row.id,
        fields_updated=list(fields_dict.keys()),
        snapshot=_to_snapshot(row),
    )


def register() -> None:
    """Enregistre le handler dans ``MUTATION_HANDLERS``.

    Appelé via ``register_mutation_handlers()`` (F55 boot).
    """
    # Effet de bord : l'import + décorateur a déjà enregistré.
    # On garde la fonction ``register()`` pour conformité avec le pattern F55.
    _ = handle_update_company_profile  # noqa: F841


__all__ = ["handle_update_company_profile", "register"]
