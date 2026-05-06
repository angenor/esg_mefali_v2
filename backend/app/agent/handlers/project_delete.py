"""F55 — Handler ``delete_project`` avec ``requires_confirmation=True`` (US3)."""

from __future__ import annotations

from app.agent.mutation_ctx import MutationCtx
from app.agent.mutation_handlers import mutation_handler
from app.agent.state import MutationResult
from app.audit.schemas import SourceOfChange
from app.orchestrator.tools.mutations.delete_project import DeleteProjectPayload
from app.projets.service import delete_projet


@mutation_handler("delete_project", requires_confirmation=True)
async def handle_delete_project(
    args: DeleteProjectPayload,
    ctx: MutationCtx,
) -> MutationResult:
    delete_projet(
        ctx.db,
        projet_id=args.projet_id,
        account_id=ctx.account_id,
        user_id=ctx.user_id,
        confirm=True,  # Confirmation déjà validée côté dispatcher (US3)
        source_of_change=SourceOfChange.LLM,
    )
    return MutationResult(
        entity_type="projet",
        entity_id=args.projet_id,
        fields_updated=["deleted_at"],
        snapshot={"deleted": True, "id": str(args.projet_id)},
    )


def register() -> None:
    _ = handle_delete_project  # noqa: F841


__all__ = ["handle_delete_project", "register"]
