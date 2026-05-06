"""F57 / US5 — Tests anti-fuite cross-thread (défense en profondeur).

Vérifie que :
- la clé du cache embedding inclut ``thread_id`` (jamais de partage cross-thread).
- ``search_long_term`` SQL filtre toujours par ``thread_id`` ET ``account_id``.
- ``recall_history`` handler scope le thread courant via ``state.thread_id``.
"""

from __future__ import annotations

import inspect
from uuid import uuid4

import pytest

from app.agent.memory import embedding_cache, long_term

pytestmark = pytest.mark.unit


def test_cache_key_includes_thread_id_no_collision() -> None:
    """US5 — deux threads avec la même query → clés différentes."""
    a = uuid4()
    b = uuid4()
    k1 = embedding_cache.make_key(str(a), "panneaux solaires")
    k2 = embedding_cache.make_key(str(b), "panneaux solaires")
    assert k1 != k2


def test_cache_key_format() -> None:
    a = uuid4()
    k = embedding_cache.make_key(str(a), "x")
    # Format = "{thread_id}:{sha256_hex}"
    parts = k.split(":")
    assert parts[0] == str(a)
    assert len(parts[-1]) == 64  # sha256 hex


def test_search_long_term_sql_includes_account_id_and_thread_id() -> None:
    """Vérifie via inspection du source que la query SQL filtre les deux."""
    src = inspect.getsource(long_term.search_long_term)
    assert "account_id = CAST(:aid AS UUID)" in src
    assert "thread_id = CAST(:tid AS UUID)" in src


def test_recall_history_uses_state_thread_id() -> None:
    """Le handler doit scope au thread du state — pas un thread arbitraire."""
    from app.agent.handlers import recall_history as rh

    src = inspect.getsource(rh.handle_recall_history)
    # La query passe explicitement state.thread_id à search_long_term
    assert "state.thread_id" in src
    # Le hash inclut la query courante (cohérent NFR-008)
    assert "hash_query" in src


def test_compactor_scopes_account_and_thread() -> None:
    """``compact_thread`` filtre toutes ses queries SQL par account_id+thread_id."""
    from app.agent.memory.compactors import (
        _select_batch_message_ids,
        _try_acquire_lock,
    )

    for fn in (_select_batch_message_ids, _try_acquire_lock):
        src = inspect.getsource(fn)
        assert "account_id = CAST(:aid AS UUID)" in src, (
            f"{fn.__name__} must filter by account_id"
        )
        assert "thread_id = CAST(:tid AS UUID)" in src or fn is _try_acquire_lock, (
            f"{fn.__name__} must filter by thread_id"
        )


def test_repository_helpers_filter_account() -> None:
    """Tous les helpers chat/memory/repository filtrent par account_id."""
    from app.chat.memory import repository

    helpers = [
        repository.get_thread_for_account,
        repository.count_messages,
        repository.count_messages_with_embedding,
        repository.purge_thread_embeddings,
        repository.clear_thread_summary,
    ]
    for fn in helpers:
        src = inspect.getsource(fn)
        assert "account_id = CAST(:aid AS UUID)" in src, (
            f"{fn.__name__} must filter by account_id (anti-fuite cross-tenant)"
        )
