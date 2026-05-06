"""F55 — Handler ``update_project`` (US1)."""

from __future__ import annotations

from typing import Any

from app.agent.mutation_ctx import MutationCtx
from app.agent.mutation_handlers import mutation_handler
from app.agent.state import MutationResult
from app.audit.schemas import SourceOfChange
from app.orchestrator.tools.mutations.update_project import UpdateProjectPayload
from app.projets.service import patch_projet


def _row_snapshot(row: Any) -> dict[str, Any]:
    try:
        return {
            "id": str(row.id),
            "version": getattr(row, "version", None),
            "nom": getattr(row, "nom", None),
            "statut": getattr(row, "statut", None),
        }
    except Exception:
        return {}


@mutation_handler("update_project")
async def handle_update_project(
    args: UpdateProjectPayload,
    ctx: MutationCtx,
) -> MutationResult:
    fields = args.fields.model_dump(exclude_none=True)
    if not fields:
        return MutationResult(
            entity_type="projet",
            entity_id=args.projet_id,
            fields_updated=[],
            snapshot={"updated": False, "reason": "no_fields_provided"},
        )

    if "montant_recherche" in fields and isinstance(fields["montant_recherche"], dict):
        money = fields["montant_recherche"]
        fields["montant_recherche"] = {
            "amount": money["amount"],
            "currency": money["currency"],
        }

    row = patch_projet(
        ctx.db,
        projet_id=args.projet_id,
        account_id=ctx.account_id,
        user_id=ctx.user_id,
        expected_version=args.expected_version,
        payload=fields,
        source_of_change=SourceOfChange.LLM,
    )
    return MutationResult(
        entity_type="projet",
        entity_id=row.id,
        fields_updated=list(fields.keys()),
        snapshot=_row_snapshot(row),
    )


def register() -> None:
    _ = handle_update_project  # noqa: F841


__all__ = ["handle_update_project", "register"]
