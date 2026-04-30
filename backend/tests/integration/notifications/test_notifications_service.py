"""F34 — Tests unitaires du service notifications (avec DB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from app.db import get_engine_migrator
from app.notifications.service import (
    InvalidNotificationKindError,
    NotificationNotFoundError,
    NotificationService,
)
from tests.integration.conftest import requires_db


def _make_account() -> uuid.UUID:
    aid = uuid.uuid4()
    Session = sessionmaker(bind=get_engine_migrator(), future=True)
    with Session() as s:
        now = datetime.now(UTC).replace(tzinfo=None)
        s.execute(
            text(
                """
                INSERT INTO account (id, name, created_at, updated_at)
                VALUES (CAST(:id AS UUID), :n, :ts, :ts)
                """
            ),
            {"id": str(aid), "n": f"acct-{aid.hex[:6]}", "ts": now},
        )
        s.commit()
    return aid


def _cleanup_account(aid: uuid.UUID) -> None:
    """Best-effort cleanup. ``audit_log`` is append-only, donc on ne peut pas
    supprimer le compte si une ligne d'audit y fait référence (FK). On supprime
    seulement les notifications. Le compte de test reste (acceptable en jeu de
    données de tests d'intégration partagés)."""
    Session = sessionmaker(bind=get_engine_migrator(), future=True)
    with Session() as s:
        s.execute(
            text("DELETE FROM notification WHERE account_id = CAST(:aid AS UUID)"),
            {"aid": str(aid)},
        )
        s.commit()


@requires_db
class TestCreate:
    def test_invalid_kind_raises(self) -> None:
        Session = sessionmaker(bind=get_engine_migrator(), future=True)
        with Session() as db:
            with pytest.raises(InvalidNotificationKindError):
                NotificationService.create_for_account(
                    db,
                    account_id=uuid.uuid4(),
                    kind="not_an_enum",
                    title="X",
                )

    def test_creates_with_payload(self) -> None:
        aid = _make_account()
        Session = sessionmaker(bind=get_engine_migrator(), future=True)
        try:
            with Session() as db:
                n = NotificationService.create_for_account(
                    db,
                    account_id=aid,
                    kind="offre_recommandee",
                    title="T",
                    body="B",
                    payload={"k": "v"},
                )
                db.commit()
                assert n.id is not None
                assert n.kind == "offre_recommandee"
                assert n.payload_json == {"k": "v"}
        finally:
            _cleanup_account(aid)


@requires_db
class TestList:
    def test_filter_unread_and_order(self) -> None:
        aid = _make_account()
        Session = sessionmaker(bind=get_engine_migrator(), future=True)
        try:
            with Session() as db:
                n1 = NotificationService.create_for_account(
                    db, account_id=aid, kind="deadline_j_minus_30", title="A"
                )
                n2 = NotificationService.create_for_account(
                    db, account_id=aid, kind="deadline_j_minus_7", title="B"
                )
                NotificationService.mark_read(
                    db, notification_id=n1.id, account_id=aid
                )
                db.commit()
                all_ = NotificationService.list_for_account(db, account_id=aid)
                assert [n.title for n in all_] == ["B", "A"]
                unread = NotificationService.list_for_account(
                    db, account_id=aid, unread=True
                )
                assert [n.id for n in unread] == [n2.id]
        finally:
            _cleanup_account(aid)

    def test_isolation_between_accounts(self) -> None:
        aid1 = _make_account()
        aid2 = _make_account()
        Session = sessionmaker(bind=get_engine_migrator(), future=True)
        try:
            with Session() as db:
                NotificationService.create_for_account(
                    db, account_id=aid1, kind="offre_recommandee", title="A1"
                )
                NotificationService.create_for_account(
                    db, account_id=aid2, kind="offre_recommandee", title="A2"
                )
                db.commit()
                lst1 = NotificationService.list_for_account(db, account_id=aid1)
                lst2 = NotificationService.list_for_account(db, account_id=aid2)
                titles1 = {n.title for n in lst1}
                titles2 = {n.title for n in lst2}
                assert titles1 == {"A1"}
                assert titles2 == {"A2"}
        finally:
            _cleanup_account(aid1)
            _cleanup_account(aid2)

    def test_limit_offset(self) -> None:
        aid = _make_account()
        Session = sessionmaker(bind=get_engine_migrator(), future=True)
        try:
            with Session() as db:
                for i in range(3):
                    NotificationService.create_for_account(
                        db,
                        account_id=aid,
                        kind="offre_recommandee",
                        title=f"T{i}",
                    )
                db.commit()
                lst = NotificationService.list_for_account(
                    db, account_id=aid, limit=1, offset=1
                )
                assert len(lst) == 1
        finally:
            _cleanup_account(aid)


@requires_db
class TestMarkRead:
    def test_404_when_not_owned(self) -> None:
        aid_owner = _make_account()
        aid_other = _make_account()
        Session = sessionmaker(bind=get_engine_migrator(), future=True)
        try:
            with Session() as db:
                n = NotificationService.create_for_account(
                    db, account_id=aid_owner, kind="offre_recommandee", title="X"
                )
                db.commit()
                with pytest.raises(NotificationNotFoundError):
                    NotificationService.mark_read(
                        db, notification_id=n.id, account_id=aid_other
                    )
        finally:
            _cleanup_account(aid_owner)
            _cleanup_account(aid_other)

    def test_idempotent(self) -> None:
        aid = _make_account()
        Session = sessionmaker(bind=get_engine_migrator(), future=True)
        try:
            with Session() as db:
                n = NotificationService.create_for_account(
                    db, account_id=aid, kind="offre_recommandee", title="Y"
                )
                db.commit()
                first = NotificationService.mark_read(
                    db, notification_id=n.id, account_id=aid
                )
                ts1 = first.read_at
                db.commit()
                second = NotificationService.mark_read(
                    db, notification_id=n.id, account_id=aid
                )
                assert second.read_at == ts1
        finally:
            _cleanup_account(aid)
