"""F02 — Script de création d'un Admin (T048).

Usage : ``python -m app.scripts.seed_admin --email a@m.io --password '...'``

- Valide la politique mot de passe.
- Crée un AccountUser role=admin, account_id=NULL.
- Idempotent : refuse si un utilisateur avec cet email existe déjà.
- Audit : ``admin.created`` source=admin.
"""

from __future__ import annotations

import argparse
import sys
import uuid
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.core.security import hash_password, validate_password_policy
from app.db import SessionLocal
from app.models.account_user import AccountUser
from app.services.audit import record_event


def create_admin(db: Session, *, email: str, password: str) -> AccountUser:
    email = email.strip().lower()
    validate_password_policy(password)
    existing = db.query(AccountUser).filter(AccountUser.email == email).first()
    if existing is not None:
        raise SystemExit(f"L'utilisateur {email} existe déjà.")
    now = datetime.now(UTC).replace(tzinfo=None)  # account_user.created_at is naive TIMESTAMP
    user = AccountUser(
        id=uuid.uuid4(),
        account_id=None,
        email=email,
        password_hash=hash_password(password),
        role="admin",
        version=1,
        created_at=now,
        updated_at=now,
    )
    db.add(user)
    db.flush()
    record_event(
        db,
        event_type="admin.created",
        actor_user_id=user.id,
        payload={"email": email},
        source_of_change="admin",
    )
    return user


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Crée un compte admin")
    parser.add_argument("--email", required=True)
    parser.add_argument("--password", required=True)
    args = parser.parse_args(argv)

    db = SessionLocal()
    try:
        user = create_admin(db, email=args.email, password=args.password)
        db.commit()
        print(f"Admin créé : id={user.id} email={user.email}")
        return 0
    except SystemExit as exc:
        db.rollback()
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        db.close()


if __name__ == "__main__":
    raise SystemExit(main())
