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
    mark_run_cancelled,
    start_run,
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
from app.db import SessionLocal

logger = logging.getLogger(__name__)


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
    else:
        ctx = ContextJson(**context_json)

    # 3. Initialisation state
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
                    yield make_error_event(
                        code="timeout",
                        message="La requête a pris trop de temps. Merci de réessayer.",
                        agent_run_id=run_id,
                    ).serialize()
                    return

                # Reconstruire un AgentState à partir du dict final
                final_state = _coerce_to_state(final_state_dict, fallback=initial_state)

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

                # 9. Compléter agent_run
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
        if run_id is not None:
            _safe_mark_cancelled(session, run_id=run_id)
        raise
    except Exception as exc:  # noqa: BLE001
        logger.exception("run_agent failed")
        if run_id is not None:
            _safe_complete(
                session,
                run_id=run_id,
                status="error",
                error_summary=str(exc)[:500],
                start_ts=start_ts,
            )
        yield make_error_event(
            code="internal",
            message="Une erreur est survenue. Merci de réessayer.",
            agent_run_id=run_id,
        ).serialize()
    finally:
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


def _safe_complete(
    session: Session,
    *,
    run_id: UUID,
    status: str,
    retry_count: int = 0,
    error_summary: str | None = None,
    start_ts: float | None = None,
) -> None:
    """UPDATE de complétion en élevant temporairement le rôle.

    Le rôle ``app_user`` n'a pas UPDATE sur ``agent_run`` ; on bascule sur
    ``app_admin`` le temps du UPDATE puis on ``RESET ROLE``.
    """
    total_latency_ms: int | None = None
    if start_ts is not None:
        total_latency_ms = int((time.perf_counter() - start_ts) * 1000)
    try:
        # Ouvre une nouvelle transaction admin
        with SessionLocal() as admin_session:
            try:
                admin_session.execute(text("SET LOCAL ROLE app_admin"))
            except Exception:
                # En dev, le rôle peut ne pas exister ; on tente sans
                logger.debug("SET LOCAL ROLE app_admin failed (dev mode?)")
            complete_run(
                admin_session,
                run_id=run_id,
                status=status,
                total_latency_ms=total_latency_ms,
                retry_count=retry_count,
                error_summary=error_summary,
            )
            admin_session.commit()
    except Exception:  # pragma: no cover - tracing must never break run
        logger.exception("Failed to complete agent_run %s", run_id)


def _safe_mark_cancelled(session: Session, *, run_id: UUID) -> None:
    """Marque un run comme cancelled (US8)."""
    try:
        with SessionLocal() as admin_session:
            try:
                admin_session.execute(text("SET LOCAL ROLE app_admin"))
            except Exception:
                pass
            mark_run_cancelled(admin_session, run_id=run_id)
            admin_session.commit()
    except Exception:  # pragma: no cover
        logger.exception("Failed to mark cancelled %s", run_id)


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


__all__ = [
    "ThreadAccessDenied",
    "make_thread_id",
    "run_agent",
]
