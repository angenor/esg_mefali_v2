"""T047 — Test integration script seed_admin."""

from __future__ import annotations

import time
import uuid

import pytest

from app.db import SessionLocal
from app.models.account_user import AccountUser
from app.scripts.seed_admin import create_admin
from tests.integration.conftest import requires_db


@requires_db
class TestSeedAdmin:
    def test_create_admin(self, valid_password):
        email = f"seed_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"
        db = SessionLocal()
        try:
            user = create_admin(db, email=email, password=valid_password)
            db.commit()
            assert user.role == "admin"
            assert user.account_id is None
            # vérifie en DB
            fetched = db.query(AccountUser).filter(AccountUser.email == email).first()
            assert fetched is not None
            assert fetched.role == "admin"
        finally:
            db.close()

    def test_create_admin_idempotence(self, valid_password):
        email = f"seed2_{int(time.time()*1000)}_{uuid.uuid4().hex[:6]}@example.com"
        db = SessionLocal()
        try:
            create_admin(db, email=email, password=valid_password)
            db.commit()
        finally:
            db.close()

        db = SessionLocal()
        try:
            with pytest.raises(SystemExit):
                create_admin(db, email=email, password=valid_password)
        finally:
            db.close()
