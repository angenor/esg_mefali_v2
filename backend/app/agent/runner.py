"""F53 / T039 — Runner ``run_agent`` : point d'entrée du graph.

Responsabilités :
- valider le ``thread_id`` composite contre l'``account_id`` (FR-013, P2 — 404
  silencieux sur mismatch) ;
- acquérir un advisory lock XACT-scoped sur le thread (Q4 clarif) ;
- enregistrer un row ``agent_run`` (start_run) ;
- exécuter le graph compilé via ``ainvoke`` (MVP F53) ;
- émettre des events SSE alignés sur le protocole F13/F55 ;
- gérer ``asyncio.CancelledError`` → ``mark_run_cancelled`` (US8) ;
- appeler ``persist_assistant_turn`` en fin de run, sauf si cancelled.

Le runner expose un ``AsyncIterator[str]`` (lignes SSE) pour pouvoir être
plugué directement dans une ``StreamingResponse(media_type="text/event-stream")``.
"""

from __future__ import annotations

import asyncio
import logging
import time
from collections.abc import AsyncIterator
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.agent.checkpointer import (
    ThreadAccountMismatchError,
    validate_thread_id,
)
from app.agent.concurrency import ThreadLockBusyError, acquire_thread_lock
from app.agent.repository import (
    complete_run,
    start_run,
    update_guardrails_flags,
)
from app.agent.sse_bridge import (
    make_done_event,
    make_error_event,
    make_token_event,
    make_validation_retry_event,
    map_dispatch_to_sse,
)
from app.agent.state import (
    AgentState,
    ContextJson,
    compose_thread_id,
    validate_thread_id_format,
)
from app.config import get_settings
from app.core.session import set_db_session_context
from app.db import SessionLocal, get_engine_migrator

logger = logging.getLogger(__name__)


def _open_admin_session() -> Session:
    """Ouvre une session pour les UPDATEs admin du runner (complete_run,
    update_guardrails_flags, mark_run_cancelled).

    Stratégie : on bind sur l'``engine_migrator`` (rôle ``migrator``) qui a
    ``BYPASSRLS`` et tous les privilèges. Cela évite trois pièges :

    1. Le rôle ``app_admin`` n'existe pas en local (seul ``migrator`` est
       garanti par la migration 0002). ``SET LOCAL ROLE app_admin`` échoue
       silencieusement et le UPDATE retombe sur ``app_user`` qui n'a pas
       le privilège.
    2. La RLS policy ``agent_run_account_isolation`` (migration 0032) ne
       gère pas le cas ``app.current_account_id = ''`` (manque NULLIF) →
       ``invalid input syntax for type uuid: \"\"`` quand la session admin
       n'a pas reçu le contexte RLS.
    3. Le pool peut retourner une connection avec une transaction sale ;
       ``rollback()`` défensif au call-site reste utile.

    L'invariant P3 (audit append-only) reste respecté : seules les colonnes
    ``agent_run`` et ``agent_run_step`` sont touchées, et uniquement par le
    runner via ces helpers.
    """
    return Session(bind=get_engine_migrator())


class ThreadAccessDenied(LookupError):
    """``thread_id`` invalide ou mismatch tenant.

    Le router doit traduire en HTTPException 404 (P2 — pas 403).
    """


async def run_agent(
    *,
    account_id: UUID,
    user_id: UUID,
    thread_id: str,
    user_message: str,
    context_json: dict[str, Any] | ContextJson | None = None,
    compiled_graph: Any | None = None,
) -> AsyncIterator[str]:
    """Exécute un tour LangGraph et yield des lignes SSE prêtes à émettre.

    Paramètres :
    - ``account_id``, ``user_id`` : identité tenant (issus de la session auth).
    - ``thread_id`` : composite ``{account_uuid}:{conv_uuid}``.
    - ``user_message`` : texte utilisateur.
    - ``context_json`` : contexte de page (page_route, entity_id, mode).
    - ``compiled_graph`` : graph LangGraph compilé. Si None, on en compile un
      à la volée (sans checkpointer — utile pour les tests).
    """
    settings = get_settings()

    # 1. Validation thread_id (FR-013)
    try:
        validate_thread_id_format(thread_id)
        validate_thread_id(thread_id, account_id=account_id)
    except (ValueError, ThreadAccountMismatchError):
        # Cross-tenant ou format invalide → 404 silencieux (pas d'indice)
        raise ThreadAccessDenied("thread_not_found") from None

    # 2. Préparation du context_json
    if context_json is None:
        ctx = ContextJson(page_route="/")
    elif isinstance(context_json, ContextJson):
        ctx = context_json
    elif isinstance(context_json, dict):
        # Filtrage : l'agent ContextJson a un champ 'page_route'. Si on reçoit
        # une autre forme de mapping (ex. chat.schemas.ContextJson sérialisée
        # avec 'page'), on adapte tolérantement.
        ctx_kwargs = dict(context_json)
        if "page" in ctx_kwargs and "page_route" not in ctx_kwargs:
            ctx_kwargs["page_route"] = ctx_kwargs.pop("page") or "/"
        # On ne garde que les clés connues du ContextJson agent
        allowed = {"page_route", "entity_id", "mode", "locale"}
        ctx_kwargs = {k: v for k, v in ctx_kwargs.items() if k in allowed and v is not None}
        if "page_route" not in ctx_kwargs:
            ctx_kwargs["page_route"] = "/"
        ctx = ContextJson(**ctx_kwargs)
    else:
        # Pydantic BaseModel (autre que ContextJson) : best effort via model_dump
        try:
            payload = context_json.model_dump()  # type: ignore[union-attr]
            ctx = ContextJson(
                page_route=payload.get("page_route") or payload.get("page") or "/",
            )
        except Exception:  # noqa: BLE001
            ctx = ContextJson(page_route="/")

    # 3. Initialisation state — agent_run_id sera renseigné après start_run
    # pour activer le tracing par-nœud (cf. graph._make_traced_node).
    initial_state = AgentState(
        thread_id=thread_id,
        account_id=account_id,
        user_id=user_id,
        user_message=user_message,
        context_json=ctx,
    )

    # 4. Compilation paresseuse si pas de graph fourni
    if compiled_graph is None:
        from app.agent.graph import compile_graph

        compiled_graph = compile_graph(checkpointer=None)

    # 5. Open DB session pour tracing + advisory lock + persistance
    session: Session = SessionLocal()
    run_id: UUID | None = None
    start_ts = time.perf_counter()
    # Flag GeneratorExit-safe : si l'``AsyncIterator`` est fermé par le
    # client (``aclose()``), Python injecte ``GeneratorExit`` qui ne
    # traverse aucun ``except Exception``. Le ``finally`` final assure
    # alors la complétion en ``cancelled``.
    run_finalized = False

    try:
        # Activer le contexte RLS (P2)
        set_db_session_context(
            session,
            user_id=user_id,
            account_id=account_id,
            is_admin=False,
        )

        # Advisory lock + start_run → tout dans une seule transaction pour
        # que le lock soit relâché à la fin du tour.
        try:
            with acquire_thread_lock(session, thread_id=thread_id, blocking=False):
                # Insérer le agent_run (le lock garantit un seul run actif/thread)
                if settings.LLM_AGENT_TRACE != "off":
                    try:
                        run_id = start_run(
                            session,
                            account_id=account_id,
                            user_id=user_id,
                            thread_id=thread_id,
                        )
                        session.commit()  # commit pour libérer le lock asap
                    except Exception:  # noqa: BLE001
                        # FK violation, RLS, etc. — on continue sans tracing
                        # plutôt que de casser le tour utilisateur
                        logger.warning(
                            "agent_run start failed (continue without tracing)",
                            exc_info=True,
                        )
                        session.rollback()
                        run_id = None

                # Propager run_id au state pour que le wrapping de tracing
                # (graph._make_traced_node) écrive un row par nœud.
                if run_id is not None:
                    initial_state.agent_run_id = run_id

                # 6. Exécuter le graph
                # MVP F53 : on appelle ainvoke (réponse complète) puis on émet
                # les events SSE en post-process. F55 polishera le streaming
                # via astream_events.
                try:
                    final_state_dict = await asyncio.wait_for(
                        compiled_graph.ainvoke(initial_state),
                        timeout=settings.LLM_AGENT_TIMEOUT_S,
                    )
                except TimeoutError:
                    if run_id is not None:
                        _safe_complete(
                            session,
                            run_id=run_id,
                            status="timeout",
                            error_summary="LLM_AGENT_TIMEOUT_S exceeded",
                            start_ts=start_ts,
                        )
                        run_finalized = True
                    yield make_error_event(
                        code="timeout",
                        message="La requête a pris trop de temps. Merci de réessayer.",
                        agent_run_id=run_id,
                    ).serialize()
                    return

                # Reconstruire un AgentState à partir du dict final
                final_state = _coerce_to_state(final_state_dict, fallback=initial_state)

                # 6.b — F57 / US9 : flush des recall_log entries staged
                # par les nodes/handlers (auto + tool) en 1 seul commit.
                _flush_recall_log_entries(final_state)

                # 7. Émettre les events
                async for line in _emit_events(final_state, run_id=run_id):
                    yield line

                # 8. Persister le message assistant (sauf si fallback vide)
                if final_state.final_text:
                    _persist_assistant(
                        session,
                        thread_id=thread_id,
                        account_id=account_id,
                        user_id=user_id,
                        content=final_state.final_text,
                    )

                # 9. Compléter agent_run + écrire les flags guardrails F58
                if run_id is not None:
                    final_status = "ok"
                    err_summary: str | None = None
                    if final_state.errors:
                        # On distingue les erreurs récupérées (ok) des non-récup
                        last = final_state.errors[-1]
                        if last.code == "validation_error" and not last.retriable:
                            final_status = "error"
                            err_summary = last.message[:500]
                    _safe_complete(
                        session,
                        run_id=run_id,
                        status=final_status,
                        retry_count=final_state.retry_count,
                        error_summary=err_summary,
                        start_ts=start_ts,
                    )
                    run_finalized = True
                    # F58 — Persiste les flags guardrails (FR-017).
                    _safe_update_guardrails_flags(
                        run_id=run_id,
                        injection_detected=getattr(
                            final_state, "injection_detected", False
                        ),
                        pii_masked_count=getattr(
                            final_state, "pii_masked_count", 0
                        ),
                        language_corrected=getattr(
                            final_state, "language_corrected", False
                        ),
                        loop_detected=getattr(final_state, "loop_detected", False),
                        circuit_breaker_open=getattr(
                            final_state, "circuit_breaker_open", False
                        ),
                        mode=settings.LLM_AGENT_MODE,
                    )

                # 10. Done event
                yield make_done_event(
                    final_text=final_state.final_text,
                    agent_run_id=run_id,
                ).serialize()

        except ThreadLockBusyError:
            yield make_error_event(
                code="conflict",
                message="Un autre tour est déjà en cours pour cette conversation.",
                agent_run_id=None,
            ).serialize()
            return

    except asyncio.CancelledError:
        # Annulation client (US8)
        if run_id is not None and not run_finalized:
            _safe_mark_cancelled(session, run_id=run_id, start_ts=start_ts)
            run_finalized = True
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("run_agent failed")
        if run_id is not None and not run_finalized:
            _safe_complete(
                session,
                run_id=run_id,
                status="error",
                error_summary=str(exc)[:500],
                start_ts=start_ts,
            )
            run_finalized = True
        yield make_error_event(
            code="internal",
            message="Une erreur est survenue. Merci de réessayer.",
            agent_run_id=run_id,
        ).serialize()
    finally:
        # ``GeneratorExit``-safe : si l'``AsyncIterator`` est fermé par le
        # client avant la fin, ni ``except CancelledError`` ni
        # ``except Exception`` ne s'exécutent, et ``completed_at`` resterait
        # NULL. On finalise ici avec status='cancelled' en best-effort.
        if run_id is not None and not run_finalized:
            try:
                _safe_mark_cancelled(
                    session, run_id=run_id, start_ts=start_ts
                )
            except Exception:  # pragma: no cover - tracing must never break
                logger.exception(
                    "Final mark_cancelled in finally failed for run %s",
                    run_id,
                )
        try:
            session.close()
        except Exception:  # noqa: BLE001
            pass


def make_thread_id(account_id: UUID, conv_id: UUID | None = None) -> str:
    """Helper : compose un thread_id ``{account}:{conv}`` (génère conv si None)."""
    return compose_thread_id(account_id=account_id, conv_id=conv_id or uuid4())


# -------------------------------------------------------------------------
# Helpers internes
# -------------------------------------------------------------------------


def _coerce_to_state(maybe: Any, *, fallback: AgentState) -> AgentState:
    """Force un dict ou AgentState en AgentState typé.

    LangGraph 1.x peut retourner un dict ou un objet selon les versions.
    """
    if isinstance(maybe, AgentState):
        return maybe
    if isinstance(maybe, dict):
        # On garde les champs reconnus uniquement
        try:
            return AgentState(**{**fallback.model_dump(), **maybe})
        except Exception:  # pragma: no cover - defensive
            return fallback
    return fallback


async def _emit_events(
    state: AgentState,
    *,
    run_id: UUID | None,
) -> AsyncIterator[str]:
    """Émet les events SSE post-exec d'un tour (tokens, tool_invoke, mutation,
    validation_retry, error éventuel).

    Note F55 : ce mapping est une version « batch » ; le streaming token-par-
    token natif sera ajouté en F55 via ``astream_events``.
    """
    # 1. Validation retry events (un par tentative invalide consommée)
    if state.errors:
        for err in state.errors:
            if err.code == "validation_error":
                tool_name = ""
                if err.details and isinstance(err.details, dict):
                    tool_name = str(err.details.get("tool_name", ""))
                yield make_validation_retry_event(
                    retry_count=state.retry_count,
                    tool_name=tool_name,
                    error_summary=err.message,
                ).serialize()

    # 2. Texte LLM en token unique (MVP F53 — F55 streamera token-par-token)
    if state.llm_response_text:
        yield make_token_event(state.llm_response_text).serialize()

    # 3. Dispatch results → tool_invoke / mutation
    for result in state.dispatch_results:
        evt = map_dispatch_to_sse(result)
        if evt is not None:
            yield evt.serialize()


def _aggregate_step_metrics(
    admin_session: Session, *, run_id: UUID
) -> tuple[int | None, int | None, str | None]:
    """Lit ``agent_run_step`` pour calculer ``total_tokens_in/out`` et
    ``final_node`` (le dernier nœud exécuté).

    Retourne ``(total_in, total_out, final_node)``. Une absence de step
    renvoie ``(None, None, None)``. Best-effort : toute exception est
    avalée en debug log.
    """
    try:
        agg = admin_session.execute(
            text(
                "SELECT "
                " COALESCE(SUM(tokens_in), NULL) AS ti, "
                " COALESCE(SUM(tokens_out), NULL) AS to_ "
                "FROM agent_run_step WHERE run_id = :rid"
            ),
            {"rid": run_id},
        ).mappings().fetchone()
        last = admin_session.execute(
            text(
                "SELECT node_name FROM agent_run_step "
                "WHERE run_id = :rid ORDER BY started_at DESC LIMIT 1"
            ),
            {"rid": run_id},
        ).fetchone()
        ti = int(agg["ti"]) if agg and agg["ti"] is not None else None
        to_val = int(agg["to_"]) if agg and agg["to_"] is not None else None
        fn = last[0] if last else None
        return ti, to_val, fn
    except Exception:  # noqa: BLE001 - tracing must never break run
        logger.debug("aggregate_step_metrics failed", exc_info=True)
        return None, None, None


def _safe_complete(
    session: Session,
    *,
    run_id: UUID,
    status: str,
    retry_count: int = 0,
    error_summary: str | None = None,
    start_ts: float | None = None,
) -> None:
    """UPDATE de complétion via une session ``migrator`` (BYPASSRLS).

    Voir :func:`_open_admin_session` pour la justification du rôle utilisé.
    Agrège ``total_tokens_in/out`` + déduit ``final_node`` depuis les
    ``agent_run_step`` déjà persistés par le wrapping de tracing.
    """
    total_latency_ms: int | None = None
    if start_ts is not None:
        total_latency_ms = int((time.perf_counter() - start_ts) * 1000)
    try:
        with _open_admin_session() as admin_session:
            admin_session.rollback()
            ti, to_val, final_node = _aggregate_step_metrics(
                admin_session, run_id=run_id
            )
            complete_run(
                admin_session,
                run_id=run_id,
                status=status,
                total_latency_ms=total_latency_ms,
                total_tokens_in=ti,
                total_tokens_out=to_val,
                retry_count=retry_count,
                final_node=final_node,
                error_summary=error_summary,
            )
            admin_session.commit()
    except Exception:  # pragma: no cover - tracing must never break run
        logger.exception("Failed to complete agent_run %s", run_id)


def _safe_update_guardrails_flags(
    *,
    run_id: UUID,
    injection_detected: bool,
    pii_masked_count: int,
    language_corrected: bool,
    loop_detected: bool,
    circuit_breaker_open: bool,
    mode: str,
) -> None:
    """F58 — UPDATE des 6 flags guardrails (FR-017). Best-effort, non bloquant."""
    try:
        with _open_admin_session() as admin_session:
            admin_session.rollback()
            update_guardrails_flags(
                admin_session,
                run_id=run_id,
                injection_detected=injection_detected,
                pii_masked_count=pii_masked_count,
                language_corrected=language_corrected,
                loop_detected=loop_detected,
                circuit_breaker_open=circuit_breaker_open,
                mode=mode,
            )
            admin_session.commit()
    except Exception:  # noqa: BLE001 - tracing must never break run
        logger.debug("Failed to update guardrails flags %s", run_id, exc_info=True)


def _safe_mark_cancelled(
    session: Session, *, run_id: UUID, start_ts: float | None = None
) -> None:
    """Marque un run comme cancelled (US8 + GeneratorExit-safe path).

    Délègue à :func:`_safe_complete` avec ``status='cancelled'`` pour
    bénéficier de l'agrégation tokens / final_node depuis les steps
    déjà persistés.
    """
    _safe_complete(
        session,
        run_id=run_id,
        status="cancelled",
        error_summary="client disconnected",
        start_ts=start_ts,
    )


def _persist_assistant(
    session: Session,
    *,
    thread_id: str,
    account_id: UUID,
    user_id: UUID,
    content: str,
) -> None:
    """Persiste le message assistant final via le service chat (F13).

    On extrait l'UUID conv du thread_id composite : conv_uuid = suffixe.
    """
    try:
        # Extraire conv_uuid (after ':')
        _, _, conv_uuid_str = thread_id.partition(":")
        conv_uuid = UUID(conv_uuid_str)

        # Le service chat attend une session qui aura déjà le RLS
        from app.chat import service as chat_service

        with SessionLocal() as chat_session:
            chat_session.rollback()  # purger pool sale (cas TestClient)
            set_db_session_context(
                chat_session,
                user_id=user_id,
                account_id=account_id,
                is_admin=False,
            )
            chat_service.persist_assistant_turn(
                chat_session,
                thread_id=conv_uuid,
                account_id=account_id,
                user_id=user_id,
                content=content,
            )
            chat_session.commit()
    except Exception:  # noqa: BLE001
        # La persistance ne MUST pas casser le SSE — on log silencieusement.
        # Cas dev : le thread chat peut ne pas exister (test isolé).
        logger.debug("persist_assistant skipped: thread chat introuvable ou err")


def _flush_recall_log_entries(state: AgentState) -> None:
    """F57 / US9 — Flush en DB les entries recall_log accumulées (auto + tool).

    Best-effort : aucune exception ne propage (le tour ne doit pas casser
    pour un tracing).
    """
    entries = list(getattr(state, "recall_log_entries", None) or [])
    if not entries:
        return
    try:
        from app.agent.memory.recall_log import flush_entries
    except Exception:  # pragma: no cover
        return
    try:
        with SessionLocal() as session:
            session.rollback()  # purger pool sale (cas TestClient)
            try:
                session.execute(
                    text(
                        f"SET LOCAL app.current_account_id = '{state.account_id}'"
                    )
                )
                if state.user_id:
                    session.execute(
                        text(
                            f"SET LOCAL app.current_user_id = '{state.user_id}'"
                        )
                    )
            except Exception:  # pragma: no cover
                session.rollback()
            flush_entries(session, entries)
            session.commit()
    except Exception:  # noqa: BLE001
        logger.debug("recall_log flush skipped (best-effort)")


__all__ = [
    "ThreadAccessDenied",
    "make_thread_id",
    "run_agent",
]
