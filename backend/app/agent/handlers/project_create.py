"""F55 — Handler ``create_project`` (US1)."""

from __future__ import annotations

from typing import Any

from app.agent.mutation_ctx import MutationCtx
from app.agent.mutation_handlers import mutation_handler
from app.agent.state import MutationResult
from app.audit.schemas import SourceOfChange
from app.orchestrator.tools.mutations.create_project import CreateProjectPayload
from app.projets.service import create_projet


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


@mutation_handler("create_project")
async def handle_create_project(
    args: CreateProjectPayload,
    ctx: MutationCtx,
) -> MutationResult:
    payload = args.model_dump(exclude_none=True)
    money = payload.get("montant_recherche")
    if money is not None and isinstance(money, dict):
        payload["montant_recherche"] = {
            "amount": money["amount"],
            "currency": money["currency"],
        }

    row = create_projet(
        ctx.db,
        account_id=ctx.account_id,
        user_id=ctx.user_id,
        payload=payload,
        source_of_change=SourceOfChange.LLM,
    )
    return MutationResult(
        entity_type="projet",
        entity_id=row.id,
        fields_updated=list(payload.keys()),
        snapshot=_row_snapshot(row),
    )


def register() -> None:
    _ = handle_create_project  # noqa: F841


__all__ = ["handle_create_project", "register"]
