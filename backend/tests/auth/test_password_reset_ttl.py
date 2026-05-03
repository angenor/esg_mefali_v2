"""F42 T048 — TTL token reset = 60 min, usage unique."""

from __future__ import annotations

import os
import time
import uuid
from collections.abc import Generator
from datetime import UTC, datetime, timedelta

import pytest

os.environ.setdefault("DISABLE_RATE_LIMIT", "1")

from sqlalchemy import text  # noqa: E402

from app.config import get_settings  # noqa: E402
from app.db import SessionLocal  # noqa: E402
from tests.conftest import DB_AVAILABLE  # noqa: E402

requires_db = pytest.mark.skipif(
    not DB_AVAILABLE,
    reason="Postgres indisponible — démarrer `docker compose up -d postgres`.",
)


@requires_db
def test_settings_password_reset_ttl_default_60():
    assert get_settings().PASSWORD_RESET_TTL_MINUTES == 60


@requires_db
def test_token_expired_raises():
    from app.auth.service import (
        InvalidResetTokenError,
        consume_password_reset,
        request_password_reset,
    )

    email = f"ttl_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"
    pwd = "Sup3rSecret!Pass"

    with SessionLocal() as db:
        # Crée un user via l'API service (register_pme attend un account, OK)
        from app.auth.service import register_pme

        register_pme(db, email=email, password=pwd)
        db.commit()

        token = request_password_reset(db, email=email)
        db.commit()
        assert token is not None

        # Force expires_at dans le passé
        db.execute(
            text(
                "UPDATE password_reset_tokens SET expires_at = :past "
                "WHERE user_id = (SELECT id FROM account_user WHERE email = :e)"
            ),
            {"past": datetime.now(UTC) - timedelta(minutes=1), "e": email.lower()},
        )
        db.commit()

        with pytest.raises(InvalidResetTokenError):
            consume_password_reset(db, token_clear=token, new_password="NewPass123!Aa")


@requires_db
def test_token_consumed_cannot_be_reused():
    from app.auth.service import (
        InvalidResetTokenError,
        consume_password_reset,
        register_pme,
        request_password_reset,
    )

    email = f"once_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"
    pwd = "Sup3rSecret!Pass"

    with SessionLocal() as db:
        register_pme(db, email=email, password=pwd)
        db.commit()
        token = request_password_reset(db, email=email)
        db.commit()
        assert token is not None
        consume_password_reset(db, token_clear=token, new_password="NewPass456!Bb")
        db.commit()
        with pytest.raises(InvalidResetTokenError):
            consume_password_reset(db, token_clear=token, new_password="OtherPass789!Cc")
