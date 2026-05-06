"""F56 — Handler MUTATION ``flag_unsourced`` (FR-005).

INSERT dans ``unsourced_flag`` avec :
- ``ON CONFLICT DO NOTHING`` sur l'index UNIQUE partiel
  ``(account_id, thread_id, lower(claim)) WHERE resolved_at IS NULL``
  (Q1 dédup intra-thread).
- ``audit_log`` row avec ``source_of_change='llm'``.
- SSE event ``unsourced_claim`` (best-effort).

Convention F55 ``@mutation_handler`` : signature
``async (args: BaseModel, ctx: MutationCtx) -> MutationResult``.
"""

from __future__ import annotations

import logging
import uuid

from sqlalchemy import text

from app.agent.mutation_ctx import MutationCtx
from app.agent.mutation_handlers import mutation_handler
from app.agent.sourcing.tool_schemas import FlagUnsourcedArgs
from app.agent.state import MutationResult

logger = logging.getLogger(__name__)


def _extract_thread_uuid(thread_id: str | None) -> str | None:
    """Extrait l'UUID conv (deuxième segment du thread_id composite)."""
    if not thread_id:
        return None
    parts = thread_id.split(":")
    if len(parts) == 2:
        return parts[1]
    return None


@mutation_handler("flag_unsourced")
async def handle_flag_unsourced(
    args: FlagUnsourcedArgs,
    ctx: MutationCtx,
) -> MutationResult:
    """Persiste un ``unsourced_flag`` (RLS account_id) + audit + SSE."""
    new_id = str(uuid.uuid4())
    # thread_id et message_id ne sont pas accessibles dans le ctx ;
    # le runner pourra enrichir via metadata si besoin. MVP : NULL.
    thread_id = None
    message_id = None

    inserted_id = ctx.db.execute(
        text(
            """
            INSERT INTO unsourced_flag
                (id, account_id, user_id, agent_run_id, thread_id, message_id,
                 claim, reason, source_of_change, created_at, updated_at, version)
            VALUES
                (CAST(:id AS UUID), CAST(:aid AS UUID), CAST(:uid AS UUID),
                 CAST(:rid AS UUID), CAST(:tid AS UUID), CAST(:mid AS UUID),
                 :claim, :reason,
                 CAST('llm' AS source_of_change_t), now(), now(), 1)
            ON CONFLICT (account_id, thread_id, lower(claim))
            WHERE resolved_at IS NULL
            DO NOTHING
            RETURNING id
            """
        ),
        {
            "id": new_id,
            "aid": str(ctx.account_id),
            "uid": str(ctx.user_id),
            "rid": str(ctx.agent_run_id) if ctx.agent_run_id else None,
            "tid": thread_id,
            "mid": message_id,
            "claim": args.claim,
            "reason": args.reason,
        },
    ).scalar()

    audit_id = None
    if inserted_id is not None:
        try:
            audit_id = ctx.audit_logger(
                entity_type="unsourced_flag",
                entity_id=uuid.UUID(str(inserted_id)),
                field=None,
                old=None,
                new={"claim": args.claim, "reason": args.reason},
                source_of_change="llm",
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("flag_unsourced audit failed: %s", exc)

        # SSE — best-effort
        try:
            await ctx.event_bus_publisher(
                ctx.account_id,
                "unsourced_claim",
                {
                    "thread_id": thread_id,
                    "message_id": message_id,
                    "agent_run_id": (
                        str(ctx.agent_run_id) if ctx.agent_run_id else None
                    ),
                    "claim": args.claim,
                    "reason": args.reason,
                    "span": None,
                    "unsourced_flag_id": str(inserted_id),
                    "auto": False,
                },
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("flag_unsourced SSE publish failed: %s", exc)

    return MutationResult(
        entity_type="unsourced_flag",
        entity_id=uuid.UUID(str(inserted_id)) if inserted_id else uuid.UUID(new_id),
        fields_updated=["claim", "reason"] if inserted_id else [],
        snapshot={"claim": args.claim, "reason": args.reason},
        audit_log_id=audit_id,
    )


def register() -> None:
    """Force le chargement du handler (idempotent)."""
    _ = handle_flag_unsourced  # noqa: F841


__all__ = ["handle_flag_unsourced", "register"]
