"""F53 / T018 — Tests d'intégration de l'advisory lock thread (concurrence)."""

from __future__ import annotations

import pytest

from app.agent.concurrency import (
    ThreadLockBusyError,
    acquire_thread_lock,
)
from app.db import SessionLocal

pytestmark = pytest.mark.integration


def test_blocking_lock_acquired_then_released() -> None:
    """Le lock blocking se prend et se libère à la fin du with."""
    with SessionLocal() as session:
        with acquire_thread_lock(session, thread_id="test-blocking-1", blocking=True):
            pass
        session.commit()


def test_non_blocking_first_acquire_succeeds() -> None:
    with SessionLocal() as session:
        with acquire_thread_lock(session, thread_id="test-nb-1", blocking=False):
            pass
        session.commit()


def test_non_blocking_second_acquire_raises_busy() -> None:
    """Si une autre session tient le lock, le 2e acquire non-blocking raise."""
    s1 = SessionLocal()
    s2 = SessionLocal()
    try:
        # s1 prend le lock
        with acquire_thread_lock(s1, thread_id="test-nb-busy", blocking=False):
            # s2 tente de le prendre → busy
            with pytest.raises(ThreadLockBusyError):
                with acquire_thread_lock(s2, thread_id="test-nb-busy", blocking=False):
                    pass
        # Après s1 commit/rollback, s2 peut le reprendre
        s1.commit()  # release lock
        with acquire_thread_lock(s2, thread_id="test-nb-busy", blocking=False):
            pass
        s2.commit()
    finally:
        s1.close()
        s2.close()


def test_different_threads_dont_conflict() -> None:
    s1 = SessionLocal()
    s2 = SessionLocal()
    try:
        with acquire_thread_lock(s1, thread_id="thread-A", blocking=False):
            with acquire_thread_lock(s2, thread_id="thread-B", blocking=False):
                pass
            s2.commit()
        s1.commit()
    finally:
        s1.close()
        s2.close()
