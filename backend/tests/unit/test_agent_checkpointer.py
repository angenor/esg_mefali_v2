"""F53 / T020 — Tests unitaires pour ``app/agent/checkpointer.py``."""

from __future__ import annotations

from uuid import uuid4

import pytest

from app.agent.checkpointer import (
    ThreadAccountMismatchError,
    _strip_sqlalchemy_dialect,
    validate_thread_id,
)

pytestmark = pytest.mark.unit


class TestValidateThreadId:
    def test_accepts_matching_prefix(self) -> None:
        a = uuid4()
        c = uuid4()
        tid = f"{a}:{c}"
        validate_thread_id(tid, account_id=a)

    def test_rejects_mismatch_prefix(self) -> None:
        a = uuid4()
        b = uuid4()
        c = uuid4()
        tid = f"{a}:{c}"
        with pytest.raises(ThreadAccountMismatchError):
            validate_thread_id(tid, account_id=b)

    def test_rejects_invalid_format(self) -> None:
        with pytest.raises(ValueError):
            validate_thread_id("not-a-thread-id", account_id=uuid4())

    def test_accepts_str_account_id(self) -> None:
        a = uuid4()
        c = uuid4()
        validate_thread_id(f"{a}:{c}", account_id=str(a))


class TestStripSqlalchemyDialect:
    def test_strips_psycopg_suffix(self) -> None:
        assert (
            _strip_sqlalchemy_dialect("postgresql+psycopg://u:p@h/d")
            == "postgresql://u:p@h/d"
        )

    def test_no_change_if_already_clean(self) -> None:
        assert (
            _strip_sqlalchemy_dialect("postgresql://u:p@h/d")
            == "postgresql://u:p@h/d"
        )

    def test_handles_other_drivers(self) -> None:
        assert (
            _strip_sqlalchemy_dialect("postgresql+asyncpg://u:p@h/d")
            == "postgresql://u:p@h/d"
        )
