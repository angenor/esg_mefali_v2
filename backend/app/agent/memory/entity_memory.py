"""F57 / US7 — Persistance résumée par entité business.

À chaque mutation business réussie (``update_company_profile``,
``project_create``/``update``/``delete``) le dispatcher F55 déclenche un
hook post-mutation qui enqueue une ``BackgroundTask`` :

1. Si l'entité business a été supprimée → ``DELETE FROM agent_entity_memory``
   pour ce ``(account_id, entity_type, entity_id)``.
2. Sinon → LLM call court (≤ 800 tokens) qui génère un fait stable, puis
   UPSERT ``agent_entity_memory`` (version++).
3. Audit log ``source_of_change='memory_system'`` (P3).

Tout échec dans le hook est journalisé et avalé : la mutation business
reste valide ; le hook re-tournera au prochain trigger (FR-014).
"""

from __future__ import annotations

import contextvars
import logging
from typing import Any
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.chat.memory.repository import (
    delete_entity_memory,
    upsert_entity_memory,
    write_audit_entity_memory,
)
from app.config import get_settings

logger = logging.getLogger(__name__)

#: Mapping ``entity_type`` → table business pour la lookup d'existence.
ENTITY_TABLE_MAP: dict[str, str] = {
    "Entreprise": "entreprise",
    "Projet": "projet",
    "Candidature": "candidature",
    "Indicateur": "indicateur",
}

#: Mapping legacy : tools dispatcher → entity_type métier.
TOOL_ENTITY_TYPE_MAP: dict[str, str] = {
    "update_company_profile": "Entreprise",
    "create_project": "Projet",
    "update_project": "Projet",
    "delete_project": "Projet",
    "create_candidature": "Candidature",
    "update_candidature": "Candidature",
    "update_indicateur_value": "Indicateur",
}

#: Ensemble des tools considérés comme DELETE (purge entity_memory).
DELETE_TOOLS: frozenset[str] = frozenset({"delete_project"})


def _set_rls_context(session: Session, *, account_id: UUID) -> None:
    try:
        session.execute(
            text(f"SET LOCAL app.current_account_id = '{account_id}'")
        )
    except Exception:  # pragma: no cover
        pass


def _entity_exists(
    session: Session,
    *,
    entity_type: str,
    entity_id: UUID,
    account_id: UUID,
) -> bool:
    """Retourne ``True`` si l'entité business existe pour ce compte."""
    table = ENTITY_TABLE_MAP.get(entity_type)
    if not table:
        return False
    try:
        sql = text(
            f"""
            SELECT 1 FROM {table}
            WHERE id = CAST(:eid AS UUID)
              AND account_id = CAST(:aid AS UUID)
            LIMIT 1
            """
        )
        row = session.execute(
            sql, {"eid": str(entity_id), "aid": str(account_id)}
        ).first()
    except Exception as exc:  # noqa: BLE001
        logger.debug("entity_memory: entity lookup failed (%s): %s", table, exc)
        return False
    return row is not None


def _build_entity_summary_prompt(
    *, entity_type: str, snapshot: dict[str, Any]
) -> tuple[str, str]:
    """Construit ``(system_prompt, user_prompt)`` pour le LLM (≤ 800 tokens)."""
    sys = (
        "Tu rédiges un fait stable factuel et court (max 5 bullets, "
        "<= 600 tokens) sur cette entité business pour un agent ESG. "
        "Reste neutre, cite uniquement des faits vérifiables. "
        "Aucune anecdote personnelle, aucune PII non sourcée. "
        "Format : bullets en français commençant par '-'."
    )
    user = (
        f"Entité : {entity_type}\n"
        f"Snapshot DB :\n{snapshot!r}\n\n"
        f"Génère un fait stable (5 bullets max)."
    )
    return sys, user


def _llm_summarize_entity(
    *, entity_type: str, snapshot: dict[str, Any]
) -> str | None:
    """Appelle le LLM pour générer un résumé. Best-effort, retourne None
    si le LLM est indisponible (le hook log warning et abandonne)."""
    sys_p, user_p = _build_entity_summary_prompt(
        entity_type=entity_type, snapshot=snapshot
    )
    try:
        from app.llm_client import get_llm_client

        settings = get_settings()
        max_tokens = int(settings.LLM_AGENT_ENTITY_MEMORY_MAX_TOKENS)
        client = get_llm_client()
        completion = client.chat.completions.create(
            model=settings.LLM_MODEL,
            messages=[
                {"role": "system", "content": sys_p},
                {"role": "user", "content": user_p},
            ],
            max_tokens=max_tokens,
            temperature=0.1,
        )
        choices = getattr(completion, "choices", None) or []
        if not choices:
            return None
        message = getattr(choices[0], "message", None)
        out = getattr(message, "content", None) if message else None
    except Exception as exc:  # noqa: BLE001
        logger.warning("entity_memory: LLM unavailable (%s)", exc)
        return None
    if not out or not str(out).strip():
        return None
    return str(out).strip()


def _load_entity_snapshot(
    session: Session,
    *,
    entity_type: str,
    entity_id: UUID,
    account_id: UUID,
) -> dict[str, Any]:
    """Charge un snapshot minimal de l'entité (best-effort, jamais lever)."""
    table = ENTITY_TABLE_MAP.get(entity_type)
    if not table:
        return {}
    try:
        row = session.execute(
            text(
                f"SELECT * FROM {table} "
                f"WHERE id = CAST(:eid AS UUID) "
                f"AND account_id = CAST(:aid AS UUID) LIMIT 1"
            ),
            {"eid": str(entity_id), "aid": str(account_id)},
        ).mappings().first()
    except Exception as exc:  # noqa: BLE001
        logger.debug("entity_memory: snapshot load failed: %s", exc)
        return {}
    if row is None:
        return {}
    out: dict[str, Any] = {}
    # Convert UUID/datetime to str for prompt readability.
    for k, v in dict(row).items():
        if v is None:
            continue
        if isinstance(v, UUID):
            out[k] = str(v)
        else:
            try:
                out[k] = v if isinstance(v, str | int | float | bool) else str(v)
            except Exception:  # noqa: BLE001
                continue
    return out


async def update_entity_memory(
    *,
    account_id: UUID,
    entity_type: str,
    entity_id: UUID,
    user_id: UUID | None = None,
    agent_run_id: UUID | None = None,
    purge: bool = False,
) -> None:
    """Refresh ou supprime l'entrée ``agent_entity_memory`` (US7).

    Best-effort : toute exception est avalée (log warning).

    Args:
        account_id: tenant courant.
        entity_type: 'Entreprise'|'Projet'|'Candidature'|'Indicateur'.
        entity_id: UUID de l'entité business.
        user_id: pour audit_log (optionnel).
        agent_run_id: traçabilité (optionnel).
        purge: si True, force DELETE (cas delete_project).
    """
    if entity_type not in ENTITY_TABLE_MAP:
        logger.debug("entity_memory: unsupported type %r", entity_type)
        return

    try:
        from app.db import SessionLocal
    except Exception as exc:  # pragma: no cover
        logger.warning("entity_memory: db import failed: %s", exc)
        return

    session: Session = SessionLocal()
    try:
        _set_rls_context(session, account_id=account_id)

        # 1. Si purge OU entité business absente → DELETE entity_memory.
        if purge or not _entity_exists(
            session,
            entity_type=entity_type,
            entity_id=entity_id,
            account_id=account_id,
        ):
            try:
                deleted = delete_entity_memory(
                    session,
                    account_id=account_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                )
                if deleted:
                    write_audit_entity_memory(
                        session,
                        account_id=account_id,
                        entity_type=entity_type,
                        entity_id=entity_id,
                        user_id=user_id,
                        operation="delete",
                        version=None,
                        agent_run_id=agent_run_id,
                    )
                session.commit()
            except Exception as exc:  # noqa: BLE001
                logger.warning("entity_memory: delete failed: %s", exc)
                session.rollback()
            return

        # 2. UPSERT — charge snapshot, génère summary, écrit, audit.
        snapshot = _load_entity_snapshot(
            session,
            entity_type=entity_type,
            entity_id=entity_id,
            account_id=account_id,
        )
        summary = _llm_summarize_entity(
            entity_type=entity_type, snapshot=snapshot
        )
        if not summary:
            # LLM indispo — on abandonne (retry au prochain trigger).
            return
        try:
            _, version = upsert_entity_memory(
                session,
                account_id=account_id,
                entity_type=entity_type,
                entity_id=entity_id,
                summary=summary,
                sources_used=[],
            )
            write_audit_entity_memory(
                session,
                account_id=account_id,
                entity_type=entity_type,
                entity_id=entity_id,
                user_id=user_id,
                operation="upsert",
                version=version,
                agent_run_id=agent_run_id,
            )
            session.commit()
        except Exception as exc:  # noqa: BLE001
            logger.warning("entity_memory: upsert failed: %s", exc)
            session.rollback()
    finally:
        try:
            session.close()
        except Exception:  # pragma: no cover
            pass


_CURRENT_STATE_CTX: contextvars.ContextVar[object | None] = contextvars.ContextVar(
    "f57_entity_memory_current_state", default=None
)


def build_before_dispatch_hook():
    """Construit un hook ``before_dispatch`` qui capte le state courant
    dans une ContextVar (lue ensuite par le ``after_dispatch`` hook)."""

    async def _hook_before(call, state) -> None:  # noqa: ANN001
        _CURRENT_STATE_CTX.set(state)

    return _hook_before


def build_after_dispatch_hook():
    """Construit un hook ``after_dispatch`` (signature dispatcher F55).

    Le hook ne lance qu'un appel async best-effort dans une nouvelle task
    asyncio (l'appelant ne peut pas attendre la mémoire entity).
    """
    import asyncio

    async def _hook(call, result) -> None:  # noqa: ANN001
        try:
            tool_name = getattr(call, "name", None) or ""
            status = getattr(result, "status", None)
            if status != "ok":
                return
            entity_type = (
                getattr(result, "entity_type", None)
                or TOOL_ENTITY_TYPE_MAP.get(tool_name)
            )
            entity_id = getattr(result, "entity_id", None)
            if not entity_type or not entity_id:
                return
            state = _CURRENT_STATE_CTX.get()
            account_id = getattr(state, "account_id", None) if state else None
            user_id = getattr(state, "user_id", None) if state else None
            agent_run_id = (
                getattr(state, "agent_run_id", None) if state else None
            )
            if account_id is None:
                # Pas de state RLS — on saute (le commit business a réussi
                # avec son RLS GUC mais le nôtre est out of scope ici).
                return
            asyncio.create_task(
                update_entity_memory(
                    account_id=account_id,
                    entity_type=entity_type,
                    entity_id=entity_id,
                    user_id=user_id,
                    agent_run_id=agent_run_id,
                    purge=tool_name in DELETE_TOOLS,
                )
            )
        except Exception as exc:  # noqa: BLE001
            logger.debug("entity_memory hook absorbed: %s", exc)

    return _hook


__all__ = [
    "DELETE_TOOLS",
    "ENTITY_TABLE_MAP",
    "TOOL_ENTITY_TYPE_MAP",
    "build_after_dispatch_hook",
    "build_before_dispatch_hook",
    "update_entity_memory",
]
