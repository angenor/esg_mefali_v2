"""F34 — Tests d'intégration des routes /me/candidatures."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime

from sqlalchemy import text

from tests.integration.conftest import requires_db


def _register_pme(client, email, password) -> dict:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    csrf = client.cookies.get("mefali_csrf")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf
    me = client.get("/me")
    assert me.status_code == 200
    return me.json()


def _engine_session():
    """Session sur l'engine principal (rôle owner ``esg``) — bypass RLS et
    accès direct aux tables catalogue (``offre``, ``fonds_source``…) sans devoir
    explicitement les granter au migrator."""
    from sqlalchemy.orm import sessionmaker

    from app.db import engine

    return sessionmaker(bind=engine, future=True)


def _make_projet_and_offre(account_id: str) -> tuple[uuid.UUID, uuid.UUID]:
    pid = uuid.uuid4()
    eid = uuid.uuid4()
    sess = _engine_session()
    now = datetime.now(UTC).replace(tzinfo=None)
    with sess() as s:
        # Crée d'abord une entreprise (FK NOT NULL pour projet)
        s.execute(
            text(
                """
                INSERT INTO entreprise (id, account_id, name, version, created_at, updated_at)
                VALUES (CAST(:id AS UUID), CAST(:aid AS UUID), :n, 1, :ts, :ts)
                """
            ),
            {"id": str(eid), "aid": account_id, "n": "E-test", "ts": now},
        )
        s.execute(
            text(
                """
                INSERT INTO projet (id, account_id, entreprise_id, nom, version, created_at, updated_at)
                VALUES (CAST(:id AS UUID), CAST(:aid AS UUID), CAST(:eid AS UUID), :n, 1, :ts, :ts)
                """
            ),
            {
                "id": str(pid),
                "aid": account_id,
                "eid": str(eid),
                "n": "P-test",
                "ts": now,
            },
        )
        existing = (
            s.execute(text("SELECT id FROM offre LIMIT 1")).mappings().first()
        )
        if existing:
            oid = existing["id"]
        else:
            fid = uuid.uuid4()
            iid = uuid.uuid4()
            oid = uuid.uuid4()
            s.execute(
                text(
                    "INSERT INTO fonds_source (id, name) "
                    "VALUES (CAST(:id AS UUID), :n)"
                ),
                {"id": str(fid), "n": "F-test"},
            )
            s.execute(
                text(
                    "INSERT INTO intermediaire (id, name, type) "
                    "VALUES (CAST(:id AS UUID), :n, 'DAE')"
                ),
                {"id": str(iid), "n": "I-test"},
            )
            s.execute(
                text(
                    "INSERT INTO offre (id, fonds_id, intermediaire_id, name) "
                    "VALUES (CAST(:id AS UUID), CAST(:fid AS UUID), CAST(:iid AS UUID), :n)"
                ),
                {
                    "id": str(oid),
                    "fid": str(fid),
                    "iid": str(iid),
                    "n": "O-test",
                },
            )
        s.commit()
    return pid, oid


def _insert_candidature(
    *,
    account_id: str,
    projet_id: uuid.UUID,
    offre_id: uuid.UUID,
    statut: str = "brouillon",
    snapshot: dict | None = None,
) -> uuid.UUID:
    cid = uuid.uuid4()
    sess = _engine_session()
    with sess() as s:
        now = datetime.now(UTC).replace(tzinfo=None)
        s.execute(
            text(
                """
                INSERT INTO candidature
                  (id, account_id, projet_id, offre_id, statut, snapshot_json,
                   version, created_at, updated_at)
                VALUES
                  (CAST(:id AS UUID), CAST(:aid AS UUID), CAST(:pid AS UUID),
                   CAST(:oid AS UUID), :st,
                   CAST(:snap AS JSONB),
                   1, :ts, :ts)
                """
            ),
            {
                "id": str(cid),
                "aid": account_id,
                "pid": str(projet_id),
                "oid": str(offre_id),
                "st": statut,
                "snap": json.dumps(snapshot) if snapshot else None,
                "ts": now,
            },
        )
        s.commit()
    return cid


def _cleanup_candidature(cid: uuid.UUID) -> None:
    sess = _engine_session()
    with sess() as s:
        s.execute(
            text("DELETE FROM candidature WHERE id = CAST(:id AS UUID)"),
            {"id": str(cid)},
        )
        s.commit()


@requires_db
class TestListCandidatures:
    def test_requires_auth(self, client) -> None:
        client.cookies.clear()
        r = client.get("/me/candidatures")
        assert r.status_code in {401, 403}

    def test_returns_empty_for_new_pme(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        r = client.get("/me/candidatures")
        assert r.status_code == 200
        assert r.json() == []

    def test_returns_candidatures_with_progression(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        pid, oid = _make_projet_and_offre(aid)
        cid = _insert_candidature(
            account_id=aid,
            projet_id=pid,
            offre_id=oid,
            snapshot={"progression_pct": 42},
        )
        try:
            r = client.get("/me/candidatures")
            assert r.status_code == 200
            body = r.json()
            assert len(body) == 1
            assert body[0]["id"] == str(cid)
            assert body[0]["progression_pct"] == 42
            assert body[0]["statut"] == "brouillon"
        finally:
            _cleanup_candidature(cid)

    def test_progression_defaults_to_zero(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        pid, oid = _make_projet_and_offre(aid)
        cid = _insert_candidature(
            account_id=aid, projet_id=pid, offre_id=oid, snapshot=None
        )
        try:
            r = client.get("/me/candidatures")
            assert r.status_code == 200
            assert r.json()[0]["progression_pct"] == 0
        finally:
            _cleanup_candidature(cid)


@requires_db
class TestUpdateStatus:
    def test_requires_auth(self, client) -> None:
        client.cookies.clear()
        r = client.patch(
            f"/me/candidatures/{uuid.uuid4()}/status",
            json={"statut": "soumise"},
        )
        assert r.status_code in {401, 403}

    def test_valid_transition(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        pid, oid = _make_projet_and_offre(aid)
        cid = _insert_candidature(account_id=aid, projet_id=pid, offre_id=oid)
        try:
            r = client.patch(
                f"/me/candidatures/{cid}/status",
                json={"statut": "soumise"},
            )
            assert r.status_code == 200, r.text
            body = r.json()
            assert body["statut"] == "soumise"
            assert body["version"] == 2
        finally:
            _cleanup_candidature(cid)

    def test_invalid_statut_returns_422(
        self, client, unique_email, valid_password
    ) -> None:
        me = _register_pme(client, unique_email, valid_password)
        aid = me["account_id"]
        pid, oid = _make_projet_and_offre(aid)
        cid = _insert_candidature(account_id=aid, projet_id=pid, offre_id=oid)
        try:
            r = client.patch(
                f"/me/candidatures/{cid}/status",
                json={"statut": "archivee"},
            )
            assert r.status_code == 422
        finally:
            _cleanup_candidature(cid)

    def test_404_when_not_owned(
        self, client, unique_email, valid_password
    ) -> None:
        me1 = _register_pme(client, unique_email, valid_password)
        aid1 = me1["account_id"]
        pid, oid = _make_projet_and_offre(aid1)
        cid = _insert_candidature(account_id=aid1, projet_id=pid, offre_id=oid)
        try:
            client.cookies.clear()
            client.headers.pop("X-CSRF-Token", None)
            email2 = f"itest_{uuid.uuid4().hex[:8]}@example.com"
            _register_pme(client, email2, valid_password)
            r = client.patch(
                f"/me/candidatures/{cid}/status",
                json={"statut": "soumise"},
            )
            assert r.status_code == 404
        finally:
            _cleanup_candidature(cid)
