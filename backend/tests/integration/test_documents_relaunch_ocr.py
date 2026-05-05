"""F50 (T077-équivalent / US8) — relance OCR via HTTP.

Couvre :
- POST ``/me/entreprise/documents/{id}/relaunch-ocr`` remet ``ocr_status``
  à ``pending`` et émet un audit ``relaunch_ocr``.
- 409 ``ocr_in_progress`` si le document est déjà en cours de traitement.
- 404 ``not_found`` si cross-tenant ou document inexistant.
- ``invalidate_existing_validation=true`` invalide ``extraction_validated_at``.

Suit le pattern intégration HTTP (TestClient + cookies CSRF + DB Postgres).
"""

from __future__ import annotations

import io
import time
import uuid as _uuid

import pytest
from sqlalchemy import text

from tests.conftest import requires_db

PDF_NATIVE = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
    b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 55>>stream\n"
    b"BT\n/F1 18 Tf\n72 720 Td\n(F50 relaunch test) Tj\nET\n"
    b"endstream\nendobj\n"
    b"5 0 obj<</Type/Font/Subtype/Type1/BaseFont/Helvetica>>endobj\n"
    b"xref\n0 6\n0000000000 65535 f \n0000000009 00000 n \n"
    b"0000000055 00000 n \n0000000101 00000 n \n0000000196 00000 n \n"
    b"0000000294 00000 n \ntrailer<</Size 6/Root 1 0 R>>\nstartxref\n349\n%%EOF"
)


def _register_pme(client, email: str, password: str) -> None:
    r = client.post("/auth/register", json={"email": email, "password": password})
    assert r.status_code in (200, 201), r.text
    csrf = client.cookies.get("mefali_csrf")
    if csrf:
        client.headers["X-CSRF-Token"] = csrf


def _provision_entreprise(client) -> None:
    r = client.get("/me/entreprise")
    assert r.status_code == 200, r.text


def _upload_pdf(client, *, payload: bytes = PDF_NATIVE):
    return client.post(
        "/me/entreprise/documents",
        files={"file": ("doc.pdf", io.BytesIO(payload), "application/pdf")},
        data={"type": "statuts"},
    )


def _unique_email(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{_uuid.uuid4().hex[:6]}@example.com"


def _force_processing(db_engine, doc_id: str) -> None:
    """Force le document en ``ocr_status='processing'`` via une connexion admin."""
    with db_engine.begin() as c:
        c.execute(text("SET LOCAL app.is_admin = 'true'"))
        c.execute(
            text(
                "UPDATE document_entreprise SET ocr_status='processing' "
                "WHERE id = CAST(:id AS UUID)"
            ),
            {"id": doc_id},
        )


@requires_db
@pytest.mark.integration
class TestRelaunchOcrSuccess:
    def test_relaunch_resets_ocr_status_and_emits_audit(
        self, client, valid_password, db_engine
    ) -> None:
        _register_pme(client, _unique_email("rl"), valid_password)
        _provision_entreprise(client)

        r = _upload_pdf(client)
        assert r.status_code == 201
        doc_id = r.json()["id"]
        assert r.json()["ocr_status"] in ("done", "deferred", "pending"), r.json()

        # Relance — le document n'est PAS en processing donc le call doit aboutir.
        rrl = client.post(
            f"/me/entreprise/documents/{doc_id}/relaunch-ocr",
            json={"invalidate_existing_validation": False},
        )
        assert rrl.status_code == 202, rrl.text
        body = rrl.json()
        assert body["id"] == doc_id
        # Le service repositionne ocr_status à 'pending' (cf. relaunch_ocr).
        assert body["ocr_status"] == "pending"

        # Vérifie en DB que le statut est bien 'pending'.
        with db_engine.connect() as c:
            c.execute(text("SET LOCAL app.is_admin = 'true'"))
            row = c.execute(
                text(
                    "SELECT ocr_status FROM document_entreprise "
                    "WHERE id = CAST(:id AS UUID)"
                ),
                {"id": doc_id},
            ).first()
        assert row is not None
        assert row[0] == "pending"

        # Audit relaunch_ocr présent (field=ocr_status).
        with db_engine.connect() as c:
            c.execute(text("SET LOCAL app.is_admin = 'true'"))
            audit = c.execute(
                text(
                    "SELECT field, new_value FROM audit_log "
                    "WHERE entity_type='document_entreprise' "
                    "AND entity_id = CAST(:id AS UUID) "
                    "AND field = 'ocr_status' "
                    "ORDER BY \"timestamp\" DESC LIMIT 1"
                ),
                {"id": doc_id},
            ).first()
        assert audit is not None, "audit relaunch_ocr manquant"
        # new_value contient {"action": "relaunch", ...}.
        assert "relaunch" in str(audit[1])

    def test_invalidate_existing_validation_resets_validated_at(
        self, client, valid_password, db_engine
    ) -> None:
        _register_pme(client, _unique_email("rli"), valid_password)
        _provision_entreprise(client)

        r = _upload_pdf(client)
        assert r.status_code == 201
        doc_id = r.json()["id"]

        # Valide d'abord pour avoir extraction_validated_at non null.
        rval = client.post(
            f"/me/entreprise/documents/{doc_id}/validate",
            json={"fields": [{"key": "raison_sociale", "value": "Acme"}]},
        )
        assert rval.status_code == 200, rval.text
        assert rval.json()["extraction_validated_at"] is not None

        # Relance avec invalidation.
        rrl = client.post(
            f"/me/entreprise/documents/{doc_id}/relaunch-ocr",
            json={"invalidate_existing_validation": True},
        )
        assert rrl.status_code == 202, rrl.text

        # Le GET document doit refléter extraction_validated_at = None.
        rget = client.get(f"/me/entreprise/documents/{doc_id}")
        assert rget.status_code == 200
        assert rget.json()["extraction_validated_at"] is None
        assert rget.json()["extraction_validated_by"] is None


@requires_db
@pytest.mark.integration
class TestRelaunchOcrConflicts:
    def test_409_when_already_processing(
        self, client, valid_password, db_engine
    ) -> None:
        _register_pme(client, _unique_email("rlp"), valid_password)
        _provision_entreprise(client)

        r = _upload_pdf(client)
        assert r.status_code == 201
        doc_id = r.json()["id"]

        # Force l'état processing en bypassant RLS via un setting admin.
        _force_processing(db_engine, doc_id)

        rrl = client.post(
            f"/me/entreprise/documents/{doc_id}/relaunch-ocr",
            json={"invalidate_existing_validation": False},
        )
        assert rrl.status_code == 409, rrl.text
        assert rrl.json()["detail"]["code"] == "ocr_in_progress"

    def test_404_when_doc_not_found(self, client, valid_password) -> None:
        _register_pme(client, _unique_email("rl404"), valid_password)
        _provision_entreprise(client)

        rrl = client.post(
            f"/me/entreprise/documents/{_uuid.uuid4()}/relaunch-ocr",
            json={"invalidate_existing_validation": False},
        )
        assert rrl.status_code == 404
        assert rrl.json()["detail"]["code"] == "not_found"

    def test_404_cross_tenant(self, client, valid_password) -> None:
        # PME A upload.
        _register_pme(client, _unique_email("rlA"), valid_password)
        _provision_entreprise(client)
        r = _upload_pdf(client)
        assert r.status_code == 201
        doc_a_id = r.json()["id"]

        # Bascule PME B.
        client.cookies.clear()
        client.headers.pop("X-CSRF-Token", None)
        _register_pme(client, _unique_email("rlB"), valid_password)
        _provision_entreprise(client)

        rrl = client.post(
            f"/me/entreprise/documents/{doc_a_id}/relaunch-ocr",
            json={"invalidate_existing_validation": False},
        )
        assert rrl.status_code == 404, "Cross-tenant doit retourner 404 (P2)"
        assert rrl.json()["detail"]["code"] == "not_found"
