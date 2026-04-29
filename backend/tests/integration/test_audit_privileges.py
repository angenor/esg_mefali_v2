"""F04 — Privilege gate (SC-002, T033).

Connects as the ``app_user`` role and asserts UPDATE/DELETE on audit_log are
rejected by Postgres privileges. This is the constitutional gate for P3.
"""

from __future__ import annotations

import os

import pytest
from sqlalchemy import create_engine, text

from tests.conftest import DB_AVAILABLE

pytestmark = pytest.mark.integration


def _app_user_engine():
    pwd = os.environ.get("APP_USER_PASSWORD")
    if not pwd:
        pytest.skip("APP_USER_PASSWORD not set — skipping privilege test")
    from app.config import get_settings

    s = get_settings()
    url = (
        f"postgresql+psycopg://app_user:{pwd}@{s.POSTGRES_HOST}:{s.POSTGRES_PORT}"
        f"/{s.POSTGRES_DB}"
    )
    return create_engine(url, pool_pre_ping=True)


@pytest.mark.skipif(not DB_AVAILABLE, reason="DB unavailable")
class TestAuditPrivileges:
    def test_app_user_can_select(self) -> None:
        engine = _app_user_engine()
        with engine.connect() as conn:
            conn.execute(text("SELECT count(*) FROM audit_log"))

    def test_app_user_cannot_update(self) -> None:
        engine = _app_user_engine()
        with engine.connect() as conn, pytest.raises(Exception) as exc:
            conn.execute(text("UPDATE audit_log SET entity_type='hacked' WHERE 1=1"))
            conn.commit()
        assert "permission" in str(exc.value).lower() or "denied" in str(exc.value).lower()

    def test_app_user_cannot_delete(self) -> None:
        engine = _app_user_engine()
        with engine.connect() as conn, pytest.raises(Exception) as exc:
            conn.execute(text("DELETE FROM audit_log WHERE 1=1"))
            conn.commit()
        assert "permission" in str(exc.value).lower() or "denied" in str(exc.value).lower()

    def test_app_user_cannot_truncate(self) -> None:
        engine = _app_user_engine()
        with engine.connect() as conn, pytest.raises(Exception) as exc:
            conn.execute(text("TRUNCATE audit_log"))
            conn.commit()
        assert "permission" in str(exc.value).lower() or "denied" in str(exc.value).lower()
