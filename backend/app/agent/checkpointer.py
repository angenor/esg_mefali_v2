"""F53 / T019 — Wrapper autour de ``AsyncPostgresSaver`` (LangGraph).

Responsabilités :
- valider que le préfixe ``account_id`` du ``thread_id`` correspond à la
  session courante (Q2 clarification — isolation tenant des checkpoints) ;
- encapsuler le ``setup()`` async appelé une seule fois au boot ;
- exposer un singleton testable.

Les tables ``checkpoints*`` ne sont PAS versionnées par Alembic ; elles
sont créées par ``AsyncPostgresSaver.setup()`` au démarrage. Cf.
``backend/alembic/README.md``.
"""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from app.agent.state import extract_account_prefix, validate_thread_id_format

logger = logging.getLogger(__name__)


class ThreadAccountMismatchError(ValueError):
    """``thread_id`` préfixé par un autre ``account_id`` que la session.

    Le runner doit traduire en 404 (FR-013, P2).
    """


def validate_thread_id(thread_id: str, *, account_id: UUID | str) -> None:
    """Vérifie que le préfixe ``thread_id`` correspond à ``account_id``.

    Lève :
    - ``ValueError`` si ``thread_id`` est mal formé.
    - ``ThreadAccountMismatchError`` si le préfixe diffère.
    """
    validate_thread_id_format(thread_id)
    prefix = extract_account_prefix(thread_id)
    expected = UUID(str(account_id))
    if prefix != expected:
        raise ThreadAccountMismatchError(
            "thread_id account prefix mismatch"
        )


# --- Async setup helper ----------------------------------------------------

_saver_singleton: Any | None = None


async def get_or_setup_async_saver(database_url: str) -> Any:
    """Retourne (et setup une fois) l'``AsyncPostgresSaver``.

    Idempotent : ``setup()`` est idempotent côté lib, mais on cache le saver
    pour éviter d'ouvrir de multiples pools.
    """
    global _saver_singleton

    if _saver_singleton is not None:
        return _saver_singleton

    # Import paresseux pour ne pas bloquer le boot quand mode == "raw"
    from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

    # AsyncPostgresSaver attend une URL postgres native (sans dialect prefix)
    pg_url = _strip_sqlalchemy_dialect(database_url)

    cm = AsyncPostgresSaver.from_conn_string(pg_url)
    saver = await cm.__aenter__()
    try:
        await saver.setup()
    except Exception:  # pragma: no cover - defensive
        logger.exception("Failed to setup AsyncPostgresSaver")
        await cm.__aexit__(None, None, None)
        raise

    _saver_singleton = saver
    return saver


def reset_saver_for_tests() -> None:
    """Reset le cache (réservé aux tests)."""
    global _saver_singleton
    _saver_singleton = None


def _strip_sqlalchemy_dialect(url: str) -> str:
    """Convertit ``postgresql+psycopg://...`` → ``postgresql://...``.

    AsyncPostgresSaver utilise psycopg directement et n'accepte pas de
    préfixe de dialect SQLAlchemy.
    """
    if "+" in url.split("://", 1)[0]:
        scheme, rest = url.split("://", 1)
        scheme = scheme.split("+", 1)[0]
        return f"{scheme}://{rest}"
    return url


__all__ = [
    "ThreadAccountMismatchError",
    "get_or_setup_async_saver",
    "reset_saver_for_tests",
    "validate_thread_id",
]
