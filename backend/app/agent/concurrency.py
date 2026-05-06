"""F53 / T017 — Helper de concurrence sur ``thread_id`` (Q4 clarification).

Sérialise les tours sur le même thread via ``pg_advisory_xact_lock`` :
- non bloquant : ``pg_try_advisory_xact_lock`` retourne True/False
- ou bloquant avec timeout configurable.

Le lock est libéré automatiquement à la fin de la transaction (XACT-scoped).
"""

from __future__ import annotations

import logging
from collections.abc import Iterator
from contextlib import contextmanager

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


class ThreadLockBusyError(RuntimeError):
    """Levée quand un autre tour LangGraph tient déjà le lock sur ce thread.

    Le runner peut soit attendre (bloquant) soit retourner 409 Conflict
    selon la stratégie choisie (cf. Q4 clarification : 2e attend ou 409).
    """


def _hash_text(thread_id: str) -> int:
    """Replicate Postgres ``hashtext`` côté client (best effort).

    En pratique on délègue à Postgres via ``pg_advisory_xact_lock(hashtext(...))``.
    Cette fonction est conservée pour les tests qui veulent prédire le bucket.
    """
    # Postgres hashtext utilise un algo spécifique ; on ne le réimplémente pas
    # ici. Cette fonction est un placeholder pour les tests.
    return hash(thread_id) & 0xFFFFFFFF


@contextmanager
def acquire_thread_lock(
    session: Session,
    *,
    thread_id: str,
    blocking: bool = True,
) -> Iterator[None]:
    """Acquiert un advisory lock XACT-scoped sur ``hashtext(thread_id)``.

    Si ``blocking=True`` (défaut), attend le relâchement.
    Si ``blocking=False``, lève ``ThreadLockBusyError`` si déjà tenu.

    Le lock est automatiquement libéré à la fin de la transaction courante.
    """
    if blocking:
        session.execute(
            text("SELECT pg_advisory_xact_lock(hashtext(:tid))"),
            {"tid": thread_id},
        )
        logger.debug("acquired blocking advisory lock for %s", thread_id)
        try:
            yield
        finally:
            # XACT-scoped → libéré automatiquement par COMMIT/ROLLBACK
            pass
    else:
        row = session.execute(
            text("SELECT pg_try_advisory_xact_lock(hashtext(:tid))"),
            {"tid": thread_id},
        ).fetchone()
        acquired = bool(row and row[0])
        if not acquired:
            raise ThreadLockBusyError(
                f"thread {thread_id} déjà verrouillé par un autre tour"
            )
        logger.debug("acquired non-blocking advisory lock for %s", thread_id)
        try:
            yield
        finally:
            pass


__all__ = ["ThreadLockBusyError", "acquire_thread_lock"]
