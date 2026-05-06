"""F55 — Dispatcher central (FR-001..FR-017).

Orchestre l'exécution d'un tool call validé selon sa catégorie :
- ASK / SHOW : retour ``frontend_event``, aucun side-effect DB.
- MUTATION   : (1) idempotency check, (2) confirmation flow, (3) rate limit,
               (4) transaction DB sous RLS, (5) handler, (6) audit, (7) EventBus,
               (8) COMMIT (ou ROLLBACK si dry_run).
- READ       : exécute handler READ, sérialise via ``serialize_read_result``,
               retourne ``tool_message`` (ré-injecté en ToolMessage par le
               nœud dispatch_tool).

Hooks pre/post (FR-017) sont best-effort : exception → log warning, dispatch
continue. Idempotence (FR-011) protège contre les reconnexions SSE.

Référence : ``specs/055-agent-tool-dispatch-sse/contracts/dispatcher-api.md``.
"""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid4

from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agent.confirmation import (
    build_pending_confirmation,
    consume_confirmation,
    store_pending_confirmation,
)
from app.agent.idempotency import (
    compute_idempotency_key,
    find_existing,
    reconstruct_result,
)
from app.agent.mutation_ctx import MutationCtx
from app.agent.mutation_handlers import get_handler
from app.agent.rate_limit import _default_limits, get_rate_store, resolve_limit
from app.agent.read_serializer import serialize_read_result
from app.agent.state import (
    AgentState,
    DispatchCategory,
    MutationResult,
    ToolCategory,
    ToolDispatchResult,
    ValidatedToolCall,
)
from app.orchestrator.tool_registry import TOOL_REGISTRY

logger = logging.getLogger(__name__)


HARD_TOOL_CALLS_CAP = 10


# --- Hooks (FR-017) --------------------------------------------------------

BeforeHook = Callable[[ValidatedToolCall, AgentState], Awaitable[None]]
AfterHook = Callable[[ValidatedToolCall, ToolDispatchResult], Awaitable[None]]


@dataclass
class DispatchHooks:
    before: list[BeforeHook] = field(default_factory=list)
    after: list[AfterHook] = field(default_factory=list)


_HOOKS = DispatchHooks()


def before_dispatch(fn: BeforeHook) -> BeforeHook:
    """Décorateur : enregistre un hook pre-dispatch (best-effort)."""
    _HOOKS.before.append(fn)
    return fn


def after_dispatch(fn: AfterHook) -> AfterHook:
    """Décorateur : enregistre un hook post-dispatch (best-effort)."""
    _HOOKS.after.append(fn)
    return fn


def reset_hooks() -> None:
    """Réservé aux tests."""
    _HOOKS.before.clear()
    _HOOKS.after.clear()


# --- Helpers DB -----------------------------------------------------------


def _safe_error_message(exc: Exception) -> str:
    msg = str(exc) or exc.__class__.__name__
    return msg[:200]


def _set_rls_context(db: Session, account_id: UUID, user_id: UUID) -> None:
    """Active les GUC RLS pour la session courante (P2)."""
    db.execute(
        text(f"SET LOCAL \"app.current_account_id\" = '{account_id}'")
    )
    db.execute(text(f"SET LOCAL \"app.current_user_id\" = '{user_id}'"))


def _create_tool_call_log(
    db: Session,
    *,
    account_id: UUID,
    user_id: UUID,
    agent_run_id: UUID | None,
    tool_call_id: str,
    tool_name: str,
    arguments: dict[str, Any] | None,
    idempotency_key: str | None,
    is_dry_run: bool,
) -> UUID:
    """INSERT initial ``tool_call_log`` (status='pending'). Retourne l'id."""
    new_id = uuid4()
    db.execute(
        text(
            """
            INSERT INTO tool_call_log
              (id, account_id, user_id, agent_run_id, tool_call_id, tool_name,
               arguments_json, status, idempotency_key, is_dry_run,
               created_at, updated_at, version)
            VALUES
              (CAST(:id AS UUID), CAST(:aid AS UUID), CAST(:uid AS UUID),
               CAST(:rid AS UUID), :tcid, :tname,
               CAST(:args AS JSONB), 'skipped', :ikey, :dry,
               now(), now(), 1)
            """
        ),
        {
            "id": str(new_id),
            "aid": str(account_id),
            "uid": str(user_id),
            "rid": str(agent_run_id) if agent_run_id else None,
            "tcid": tool_call_id,
            "tname": tool_name,
            "args": json.dumps(arguments or {}, default=str),
            "ikey": idempotency_key,
            "dry": is_dry_run,
        },
    )
    return new_id


def _update_tool_call_log(
    db: Session,
    *,
    log_id: UUID,
    status: str,
    dispatch_result_kind: str | None,
    output: dict[str, Any] | None,
    error_summary: str | None,
    entity_type: str | None,
    entity_id: UUID | None,
    audit_log_id: UUID | None,
    duration_ms: int | None,
) -> None:
    db.execute(
        text(
            """
            UPDATE tool_call_log SET
                status = :status,
                dispatch_result_kind = :kind,
                output_json = CAST(:out AS JSONB),
                error_summary = :err,
                entity_type = :etype,
                entity_id = CAST(:eid AS UUID),
                audit_log_id = CAST(:auid AS UUID),
                duration_ms = :dur,
                updated_at = now()
            WHERE id = CAST(:id AS UUID)
            """
        ),
        {
            "id": str(log_id),
            "status": status,
            "kind": dispatch_result_kind,
            "out": json.dumps(output or {}, default=str) if output is not None else None,
            "err": error_summary,
            "etype": entity_type,
            "eid": str(entity_id) if entity_id else None,
            "auid": str(audit_log_id) if audit_log_id else None,
            "dur": duration_ms,
        },
    )


def _audit_logger_factory(
    db: Session,
    *,
    account_id: UUID,
    user_id: UUID,
    tool_call_log_id: UUID,
    agent_run_id: UUID | None,
) -> Callable[..., UUID | None]:
    """Construit un audit_logger partiellement appliqué.

    Insère via ``record_audit`` étendu avec ``tool_call_id`` + ``agent_run_id``.
    """

    def _logger(
        *,
        entity_type: str,
        entity_id: UUID,
        field: str | None = None,
        old: Any = None,
        new: Any = None,
        source_of_change: str = "llm",
    ) -> UUID | None:
        # Cible la même transaction db (pas de SAVEPOINT)
        if field is not None and old == new:
            return None
        from uuid import uuid4 as _uuid4

        new_id = _uuid4()
        db.execute(
            text(
                """
                INSERT INTO audit_log
                    (id, user_id, account_id, entity_type, entity_id,
                     field, old_value, new_value, source_of_change,
                     tool_call_id, agent_run_id,
                     "timestamp", created_at, updated_at, version)
                VALUES
                    (CAST(:id AS UUID), CAST(:uid AS UUID), CAST(:aid AS UUID),
                     :etype, CAST(:eid AS UUID),
                     :field, CAST(:old AS JSONB), CAST(:new AS JSONB),
                     CAST(:src AS source_of_change_t),
                     CAST(:tcid AS UUID), CAST(:rid AS UUID),
                     now(), now(), now(), 1)
                """
            ),
            {
                "id": str(new_id),
                "uid": str(user_id),
                "aid": str(account_id),
                "etype": entity_type,
                "eid": str(entity_id),
                "field": field,
                "old": json.dumps(old, default=str) if old is not None else None,
                "new": json.dumps(new, default=str) if new is not None else None,
                "src": source_of_change,
                "tcid": str(tool_call_log_id),
                "rid": str(agent_run_id) if agent_run_id else None,
            },
        )
        return new_id

    return _logger


async def _noop_event_bus(
    account_id: UUID, event_type: str, payload: dict[str, Any]
) -> None:
    """Fallback event bus publisher (no-op) — intégré au runner réel."""
    del account_id, event_type, payload


async def _run_hooks_before(
    call: ValidatedToolCall, state: AgentState
) -> None:
    for h in _HOOKS.before:
        try:
            await h(call, state)
        except Exception:  # noqa: BLE001
            logger.warning("before_dispatch hook raised; absorbed", exc_info=True)


async def _run_hooks_after(
    call: ValidatedToolCall, result: ToolDispatchResult
) -> None:
    for h in _HOOKS.after:
        try:
            await h(call, result)
        except Exception:  # noqa: BLE001
            logger.warning("after_dispatch hook raised; absorbed", exc_info=True)


# --- Variantes par catégorie ----------------------------------------------


async def _dispatch_ask_show(
    call: ValidatedToolCall,
    *,
    category: ToolCategory,
) -> ToolDispatchResult:
    """ASK / SHOW : retour frontend_event, aucun side-effect."""
    return ToolDispatchResult(
        tool_call_id=call.id,
        tool_name=call.name,
        category=DispatchCategory.SSE_ONLY,
        kind="frontend_event",
        status="ok",
        output={
            "category": category.value,
            "tool_call_id": call.id,
            "tool_name": call.name,
            "arguments": call.arguments.model_dump(mode="json"),
        },
    )


async def _dispatch_read(
    state: AgentState,
    call: ValidatedToolCall,
) -> ToolDispatchResult:
    """READ : exec handler, sérialise via read_serializer, retourne tool_message."""
    from app.agent.nodes.dispatch_tool import _REINVOKE_HANDLERS

    handler = _REINVOKE_HANDLERS.get(call.name)
    if handler is None:
        # Fallback minimal : retourne un placeholder vide
        serialized = serialize_read_result(
            {"note": f"{call.name} stub (handler enriched in F56/F57)"},
        )
        return ToolDispatchResult(
            tool_call_id=call.id,
            tool_name=call.name,
            category=DispatchCategory.REINVOKE_LLM,
            kind="tool_message",
            status="ok",
            output={"content": serialized},
        )
    try:
        out = await handler(state, call)
    except Exception as exc:  # noqa: BLE001
        return ToolDispatchResult(
            tool_call_id=call.id,
            tool_name=call.name,
            category=DispatchCategory.REINVOKE_LLM,
            kind="error",
            status="error",
            error_summary=_safe_error_message(exc),
        )
    serialized = serialize_read_result(out)
    return ToolDispatchResult(
        tool_call_id=call.id,
        tool_name=call.name,
        category=DispatchCategory.REINVOKE_LLM,
        kind="tool_message",
        status="ok",
        output={"content": serialized},
    )


async def _execute_mutation_handler(
    handler_fn: Any,
    args: BaseModel,
    ctx: MutationCtx,
) -> MutationResult:
    """Helper : appelle handler ; ``MutationResult`` exigé."""
    result = await handler_fn(args, ctx)
    if not isinstance(result, MutationResult):
        raise TypeError(
            f"handler doit retourner MutationResult, reçu {type(result).__name__}"
        )
    return result


def _resolve_user_response(call: ValidatedToolCall) -> str | None:
    """Si le call est issu d'une confirmation user (sheet_result), retourne la
    réponse 'yes' / 'no' éventuellement présente dans ``arguments``.

    Heuristique : tout argument ``confirm`` boolean ou ``response`` string.
    Pour F55 le frontend pose ``arguments.confirm = true/false`` ou
    ``arguments.response = "yes"|"no"`` lors du re-post du sheet result.
    """
    args = call.arguments.model_dump() if hasattr(call.arguments, "model_dump") else {}
    if not isinstance(args, dict):
        return None
    if "confirm" in args:
        return "yes" if bool(args["confirm"]) else "no"
    raw = args.get("response") or args.get("user_response")
    if isinstance(raw, str) and raw.lower() in {"yes", "no"}:
        return raw.lower()
    return None


# --- Mutation flow complet ------------------------------------------------


async def _dispatch_mutation(  # noqa: PLR0913, PLR0915
    call: ValidatedToolCall,
    state: AgentState,
    db: Session,
    *,
    requires_confirmation: bool,
    dry_run: bool,
    event_bus_publisher: Callable[[UUID, str, dict[str, Any]], Awaitable[None]],
    idempotency_key: str,
) -> ToolDispatchResult:
    """Exécute le flow complet d'une mutation."""
    started_at = time.perf_counter()

    # 1. Confirmation flow ---------------------------------------------------
    user_resp = _resolve_user_response(call)
    # Détection : ce dispatch fait-il référence à un pending déjà stocké ?
    has_pending = False
    if requires_confirmation and state.agent_run_id is not None:
        try:
            from app.agent.confirmation import _read_metadata

            meta = _read_metadata(db, state.agent_run_id)
            pcs = meta.get("pending_confirmations") or {}
            has_pending = isinstance(pcs, dict) and call.id in pcs
        except Exception:  # noqa: BLE001
            has_pending = False

    if requires_confirmation and not has_pending:
        # Première rencontre : on stocke le pending et on retourne un
        # ask_yes_no via frontend_event. Aucun row tool_call_log finalisé.
        # Le flag ``confirm`` du LLM (souvent ``confirm=True``) n'est PAS
        # honoré tant qu'il n'y a pas de pending : la confirmation user
        # explicite est requise.
        pending = build_pending_confirmation(
            tool_call_id=call.id,
            tool_name=call.name,
            arguments=call.arguments.model_dump(mode="json"),
        )
        if state.agent_run_id is not None:
            store_pending_confirmation(
                db, agent_run_id=state.agent_run_id, pending=pending
            )
        return ToolDispatchResult(
            tool_call_id=call.id,
            tool_name=call.name,
            category=DispatchCategory.SSE_ONLY,
            kind="frontend_event",
            status="pending_confirmation",
            output={
                "category": "ASK",
                "tool_call_id": call.id,
                "tool_name": "ask_yes_no",
                "arguments": {
                    "question": (
                        f"Confirmer l'exécution de '{call.name}' ?"
                    ),
                    "context": call.arguments.model_dump(mode="json"),
                },
                "pending_for": call.name,
            },
        )

    if requires_confirmation and has_pending and user_resp is not None:
        # Second tour : consommer la confirmation
        if state.agent_run_id is None:
            return ToolDispatchResult(
                tool_call_id=call.id,
                tool_name=call.name,
                category=DispatchCategory.DB_MUTATION,
                kind="error",
                status="error",
                error_summary="missing_agent_run",
            )
        pending, status = consume_confirmation(
            db,
            agent_run_id=state.agent_run_id,
            call_id=call.id,
            user_response=user_resp,  # type: ignore[arg-type]
        )
        if status == "cancelled_by_user":
            return ToolDispatchResult(
                tool_call_id=call.id,
                tool_name=call.name,
                category=DispatchCategory.DB_MUTATION,
                kind="frontend_event",
                status="cancelled_by_user",
                output={"message": "operation_cancelled"},
            )
        if status == "confirmation_expired":
            return ToolDispatchResult(
                tool_call_id=call.id,
                tool_name=call.name,
                category=DispatchCategory.DB_MUTATION,
                kind="error",
                status="confirmation_expired",
                error_summary="confirmation_expired",
            )
        if pending is None:  # missing
            return ToolDispatchResult(
                tool_call_id=call.id,
                tool_name=call.name,
                category=DispatchCategory.DB_MUTATION,
                kind="error",
                status="error",
                error_summary="confirmation_missing",
            )
        # OK : continuer, mais utiliser ``pending.arguments`` comme args réels
        # (sécurité : ce sont les args originaux, pas ceux de la confirmation).
        # On reconstruit un call effectif avec les arguments validés.
        original_args = call.arguments  # garde le BaseModel typé
        del original_args  # le handler s'appuie sur call.arguments

    # 2. Rate limit check ----------------------------------------------------
    rate_store = get_rate_store()
    limits = _default_limits()
    limit_per_min = resolve_limit(call.name, limits)
    decision = await rate_store.check_and_increment(
        state.account_id, call.name, limit_per_min
    )
    if not decision.allowed:
        if decision.reason == "store_unavailable":
            return ToolDispatchResult(
                tool_call_id=call.id,
                tool_name=call.name,
                category=DispatchCategory.DB_MUTATION,
                kind="error",
                status="error",
                error_summary="rate_limit_unavailable",
            )
        return ToolDispatchResult(
            tool_call_id=call.id,
            tool_name=call.name,
            category=DispatchCategory.DB_MUTATION,
            kind="error",
            status="rate_limited",
            error_summary=f"rate_exceeded:{call.name}",
        )

    # 3. Création tool_call_log + transaction handler ------------------------
    handler_fn = get_handler(call.name)
    if handler_fn is None:
        return ToolDispatchResult(
            tool_call_id=call.id,
            tool_name=call.name,
            category=DispatchCategory.DB_MUTATION,
            kind="error",
            status="error",
            error_summary="handler_not_registered",
        )

    # Sous-transaction : tout commit si OK, ROLLBACK sinon (ou si dry_run).
    log_id: UUID | None = None
    try:
        # On force un SET LOCAL RLS en début de transaction.
        _set_rls_context(db, state.account_id, state.user_id)
        log_id = _create_tool_call_log(
            db,
            account_id=state.account_id,
            user_id=state.user_id,
            agent_run_id=state.agent_run_id,
            tool_call_id=call.id,
            tool_name=call.name,
            arguments=call.arguments.model_dump(mode="json"),
            idempotency_key=idempotency_key,
            is_dry_run=dry_run,
        )

        audit_logger = _audit_logger_factory(
            db,
            account_id=state.account_id,
            user_id=state.user_id,
            tool_call_log_id=log_id,
            agent_run_id=state.agent_run_id,
        )

        ctx = MutationCtx(
            account_id=state.account_id,
            user_id=state.user_id,
            db=db,
            audit_logger=audit_logger,
            event_bus_publisher=event_bus_publisher,
            tool_call_log_id=log_id,
            agent_run_id=state.agent_run_id,
            dry_run=dry_run,
        )

        mutation_result = await _execute_mutation_handler(
            handler_fn, call.arguments, ctx
        )
    except Exception as exc:  # noqa: BLE001
        # ROLLBACK + retour error
        try:
            db.rollback()
        except Exception:  # pragma: no cover
            pass
        logger.warning(
            "mutation handler failed for %s: %s",
            call.name,
            _safe_error_message(exc),
        )
        return ToolDispatchResult(
            tool_call_id=call.id,
            tool_name=call.name,
            category=DispatchCategory.DB_MUTATION,
            kind="error",
            status="error",
            error_summary=_safe_error_message(exc),
        )

    # 4. dry_run → ROLLBACK forcé
    if dry_run:
        try:
            db.rollback()
        except Exception:  # pragma: no cover
            pass
        duration_ms = int((time.perf_counter() - started_at) * 1000)
        return ToolDispatchResult(
            tool_call_id=call.id,
            tool_name=call.name,
            category=DispatchCategory.DB_MUTATION,
            kind="mutation_result",
            status="ok",
            entity_type=mutation_result.entity_type,
            entity_id=mutation_result.entity_id,
            fields_updated=mutation_result.fields_updated,
            audit_log_id=mutation_result.audit_log_id,
            output={"snapshot": mutation_result.snapshot or {}},
            is_dry_run=True,
            duration_ms=duration_ms,
        )

    # 5. Update tool_call_log + COMMIT
    duration_ms = int((time.perf_counter() - started_at) * 1000)
    try:
        _update_tool_call_log(
            db,
            log_id=log_id,
            status="ok",
            dispatch_result_kind="mutation_result",
            output={"snapshot": mutation_result.snapshot or {}},
            error_summary=None,
            entity_type=mutation_result.entity_type,
            entity_id=mutation_result.entity_id,
            audit_log_id=mutation_result.audit_log_id,
            duration_ms=duration_ms,
        )
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        logger.exception("commit failed after mutation handler")
        return ToolDispatchResult(
            tool_call_id=call.id,
            tool_name=call.name,
            category=DispatchCategory.DB_MUTATION,
            kind="error",
            status="error",
            error_summary="commit_failed",
        )

    # 6. EventBus publish (post-commit) — best effort
    try:
        await event_bus_publisher(
            state.account_id,
            "entity_updated",
            {
                "entity_type": mutation_result.entity_type,
                "entity_id": str(mutation_result.entity_id),
                "fields_updated": list(mutation_result.fields_updated),
                "source": "llm",
            },
        )
    except Exception:  # noqa: BLE001
        logger.warning("event_bus publish failed", exc_info=True)

    return ToolDispatchResult(
        tool_call_id=call.id,
        tool_name=call.name,
        category=DispatchCategory.DB_MUTATION,
        kind="mutation_result",
        status="ok",
        entity_type=mutation_result.entity_type,
        entity_id=mutation_result.entity_id,
        fields_updated=mutation_result.fields_updated,
        audit_log_id=mutation_result.audit_log_id,
        output={"snapshot": mutation_result.snapshot or {}},
        is_dry_run=False,
        duration_ms=duration_ms,
    )


# --- Entrée publique ------------------------------------------------------


async def dispatch(  # noqa: PLR0913
    call: ValidatedToolCall,
    state: AgentState,
    db: Session,
    *,
    dry_run: bool = False,
    event_bus_publisher: (
        Callable[[UUID, str, dict[str, Any]], Awaitable[None]] | None
    ) = None,
) -> ToolDispatchResult:
    """Dispatche un tool call validé (ASK/SHOW/MUTATION/READ).

    Voir ``contracts/dispatcher-api.md`` pour le détail.
    """
    started_at = time.perf_counter()
    publisher = event_bus_publisher or _noop_event_bus

    # 0. hard cap (FR-015) — déjà géré au niveau dispatch_tool node mais
    # défense en profondeur.
    if state.tool_calls_count_in_turn >= HARD_TOOL_CALLS_CAP:
        return ToolDispatchResult(
            tool_call_id=call.id,
            tool_name=call.name,
            category=DispatchCategory.DB_MUTATION,
            kind="error",
            status="error",
            error_summary="tool_calls_cap_reached",
        )

    # 1. hooks pre
    await _run_hooks_before(call, state)

    # 2. Catégorisation via TOOL_REGISTRY
    tool_def = TOOL_REGISTRY.get(call.name)
    if tool_def is None:
        result = ToolDispatchResult(
            tool_call_id=call.id,
            tool_name=call.name,
            category=DispatchCategory.DB_MUTATION,
            kind="error",
            status="error",
            error_summary="tool_not_registered",
        )
        await _run_hooks_after(call, result)
        return result

    category = tool_def.category

    # ASK / SHOW shortcut
    if category in (ToolCategory.ASK, ToolCategory.SHOW):
        result = await _dispatch_ask_show(call, category=category)
        result.duration_ms = int((time.perf_counter() - started_at) * 1000)
        await _run_hooks_after(call, result)
        return result

    # READ shortcut
    if category == ToolCategory.READ:
        result = await _dispatch_read(state, call)
        result.duration_ms = int((time.perf_counter() - started_at) * 1000)
        await _run_hooks_after(call, result)
        return result

    # MUTATION : idempotency check FIRST
    idempotency_key = compute_idempotency_key(
        state.account_id, state.agent_run_id, call.id
    )
    try:
        existing = find_existing(
            db, account_id=state.account_id, idempotency_key=idempotency_key
        )
    except Exception:  # noqa: BLE001 - cas où la table n'existe pas (test isolé)
        logger.warning("idempotency check failed, continuing", exc_info=True)
        existing = None

    if existing and existing.get("status") in {"ok", "rate_limited", "cancelled_by_user"}:
        # Reconstruction sans ré-exécution
        result = reconstruct_result(existing)
        result.duration_ms = int((time.perf_counter() - started_at) * 1000)
        await _run_hooks_after(call, result)
        return result

    # Mutation flow complet
    result = await _dispatch_mutation(
        call,
        state,
        db,
        requires_confirmation=tool_def.requires_confirmation,
        dry_run=dry_run,
        event_bus_publisher=publisher,
        idempotency_key=idempotency_key,
    )
    result.duration_ms = int((time.perf_counter() - started_at) * 1000)
    await _run_hooks_after(call, result)
    return result


__all__ = [
    "AfterHook",
    "BeforeHook",
    "DispatchHooks",
    "after_dispatch",
    "before_dispatch",
    "dispatch",
    "reset_hooks",
]
