"""F50 (T016/T017/T032/T033) — tests intégration HTTP des extensions documents.

Couvre :
- ``GET /me/documents/by-fingerprint`` (pre-flight dédoublonnage SHA-256).
- ``POST /me/entreprise/documents`` avec ``link_projet_id`` (upload + lien M:N).
- ``POST /me/entreprise/documents/{id}/validate`` (validation extraction +
  audit ``validate_extraction``).
- 409 ``already_validated`` quand un document est revalidé sans flag de
  re-correction.

Suit le pattern de ``tests/integration/entreprise/test_documents_api.py`` pour
les fixtures (auth PME via cookies, RLS via middleware).
"""

from __future__ import annotations

import hashlib
import io
import time
import uuid as _uuid

import pytest
from sqlalchemy import text

from tests.conftest import requires_db
from tests.integration.conftest import requires_db as integration_requires_db  # noqa: F401

PDF_NATIVE = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
    b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 55>>stream\n"
    b"BT\n/F1 18 Tf\n72 720 Td\n(F50 fingerprint) Tj\nET\n"
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


def _create_projet(client, *, nom: str = "Solar Akwaba") -> str:
    r = client.post(
        "/me/projets",
        json={"nom": nom, "statut": "brouillon"},
    )
    assert r.status_code in (200, 201), r.text
    return r.json()["id"]


def _upload_pdf(
    client,
    *,
    data: bytes = PDF_NATIVE,
    doc_type: str = "statuts",
    filename: str = "doc.pdf",
    link_projet_id: str | None = None,
):
    form: dict[str, str] = {"type": doc_type}
    if link_projet_id is not None:
        form["link_projet_id"] = link_projet_id
    return client.post(
        "/me/entreprise/documents",
        files={"file": (filename, io.BytesIO(data), "application/pdf")},
        data=form,
    )


def _unique_email(prefix: str) -> str:
    return f"{prefix}_{int(time.time() * 1000)}_{_uuid.uuid4().hex[:6]}@example.com"


# ---------------------------------------------------------------------------
# T016 — by-fingerprint
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.integration
class TestByFingerprint:
    def test_200_when_duplicate_exists_same_account(
        self, client, valid_password
    ) -> None:
        _register_pme(client, _unique_email("fp"), valid_password)
        _provision_entreprise(client)

        r = _upload_pdf(client, doc_type="statuts", filename="s.pdf")
        assert r.status_code == 201, r.text
        sha = hashlib.sha256(PDF_NATIVE).hexdigest()

        rfp = client.get("/me/documents/by-fingerprint", params={"sha256": sha})
        assert rfp.status_code == 200, rfp.text
        body = rfp.json()
        assert "document" in body
        assert body["document"]["content_sha256"] == sha
        assert body["document"]["mime_type"] == "application/pdf"

    def test_404_when_no_duplicate(self, client, valid_password) -> None:
        _register_pme(client, _unique_email("fp404"), valid_password)
        _provision_entreprise(client)

        sha = hashlib.sha256(b"unknown content").hexdigest()
        r = client.get("/me/documents/by-fingerprint", params={"sha256": sha})
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "not_found"

    def test_400_when_invalid_hex(self, client, valid_password) -> None:
        _register_pme(client, _unique_email("fpbad"), valid_password)
        _provision_entreprise(client)

        # Trop court / non hex.
        r = client.get(
            "/me/documents/by-fingerprint", params={"sha256": "not-a-hex-string"}
        )
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "invalid_fingerprint"

        # Longueur incorrecte (63 chars).
        r = client.get(
            "/me/documents/by-fingerprint", params={"sha256": "a" * 63}
        )
        assert r.status_code == 400
        assert r.json()["detail"]["code"] == "invalid_fingerprint"

    def test_404_cross_tenant(self, client, valid_password) -> None:
        # PME A upload.
        _register_pme(client, _unique_email("fpA"), valid_password)
        _provision_entreprise(client)
        r = _upload_pdf(client)
        assert r.status_code == 201
        sha = hashlib.sha256(PDF_NATIVE).hexdigest()

        # Bascule PME B.
        client.cookies.clear()
        client.headers.pop("X-CSRF-Token", None)
        _register_pme(client, _unique_email("fpB"), valid_password)
        _provision_entreprise(client)

        rfp = client.get("/me/documents/by-fingerprint", params={"sha256": sha})
        assert rfp.status_code == 404, "Cross-tenant doit retourner 404 (P2)"
        assert rfp.json()["detail"]["code"] == "not_found"


# ---------------------------------------------------------------------------
# T017 — upload + link_projet_id
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.integration
class TestUploadWithLinkProjet:
    def test_creates_link_and_audit(
        self, client, valid_password, db_engine
    ) -> None:
        _register_pme(client, _unique_email("ul"), valid_password)
        _provision_entreprise(client)
        projet_id = _create_projet(client, nom="Projet Solaire AKW")

        r = _upload_pdf(client, link_projet_id=projet_id)
        assert r.status_code == 201, r.text
        body = r.json()
        doc_id = body["id"]
        assert projet_id in body["linked_projets"]

        # Vérifie ligne document_link_projet via une connexion privilégiée
        # (admin context bypass RLS via app.is_admin=true).
        with db_engine.connect() as c:
            c.execute(text("SET LOCAL app.is_admin = 'true'"))
            row = c.execute(
                text(
                    "SELECT document_id, projet_id, account_id "
                    "FROM document_link_projet "
                    "WHERE document_id = CAST(:did AS UUID) "
                    "AND projet_id = CAST(:pid AS UUID)"
                ),
                {"did": doc_id, "pid": projet_id},
            ).first()
        assert row is not None, "ligne document_link_projet manquante"

        # Audit `link_projet` doit avoir été émis (notes contient
        # 'document_link_projet.created' — best-effort: on filtre sur
        # entity_type=document_link_projet).
        with db_engine.connect() as c:
            c.execute(text("SET LOCAL app.is_admin = 'true'"))
            audit_rows = c.execute(
                text(
                    "SELECT entity_type, source_of_change FROM audit_log "
                    "WHERE entity_type = 'document_link_projet' "
                    "ORDER BY \"timestamp\" DESC LIMIT 5"
                )
            ).all()
        assert any(
            r[0] == "document_link_projet" for r in audit_rows
        ), f"audit document_link_projet manquant : {audit_rows}"

    def test_invalid_uuid_returns_422(self, client, valid_password) -> None:
        _register_pme(client, _unique_email("ulbad"), valid_password)
        _provision_entreprise(client)

        # H2 : link_projet_id non-UUID doit produire 422 invalid_projet_id
        # (et non 500 sur CAST PG).
        r = _upload_pdf(client, link_projet_id="not-a-uuid")
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["code"] == "invalid_projet_id"

    def test_unknown_projet_id_returns_422(self, client, valid_password) -> None:
        _register_pme(client, _unique_email("ul404"), valid_password)
        _provision_entreprise(client)

        r = _upload_pdf(client, link_projet_id=str(_uuid.uuid4()))
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["code"] == "projet_not_found"


# ---------------------------------------------------------------------------
# T032 — validate propage et audite
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.integration
class TestValidateExtraction:
    def test_validate_emits_audit_and_fills_validation_fields(
        self, client, valid_password, db_engine
    ) -> None:
        _register_pme(client, _unique_email("vx"), valid_password)
        _provision_entreprise(client)

        r = _upload_pdf(client)
        assert r.status_code == 201
        doc_id = r.json()["id"]

        # Validate avec quelques champs et propagation entreprise.
        rval = client.post(
            f"/me/entreprise/documents/{doc_id}/validate",
            json={
                "fields": [
                    {"key": "raison_sociale", "value": "Acme SARL"},
                    {"key": "effectifs", "value": 18},
                ],
                "propagate_to": [],
            },
        )
        assert rval.status_code == 200, rval.text
        body = rval.json()
        assert body["id"] == doc_id
        assert body["extraction_validated_at"] is not None
        assert body["extraction_validated_by"] is not None

        # GET doc renvoie maintenant les champs renseignés.
        rget = client.get(f"/me/entreprise/documents/{doc_id}")
        assert rget.status_code == 200
        det = rget.json()
        assert det["extraction_validated_at"] is not None
        assert det["extraction_validated_by"] is not None

        # Audit row contient validate_extraction (entity_type=document_entreprise,
        # field=extraction_validated_at).
        with db_engine.connect() as c:
            c.execute(text("SET LOCAL app.is_admin = 'true'"))
            rows = c.execute(
                text(
                    "SELECT field FROM audit_log "
                    "WHERE entity_type='document_entreprise' "
                    "AND entity_id = CAST(:id AS UUID) "
                    "ORDER BY \"timestamp\" DESC"
                ),
                {"id": doc_id},
            ).all()
        fields = {r[0] for r in rows}
        assert "extraction_validated_at" in fields, f"audit fields={fields}"


# ---------------------------------------------------------------------------
# T033 — validate already_validated → 409
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.integration
class TestValidateAlreadyValidated:
    def test_409_when_document_already_validated(
        self, client, valid_password
    ) -> None:
        _register_pme(client, _unique_email("v2"), valid_password)
        _provision_entreprise(client)

        r = _upload_pdf(client)
        assert r.status_code == 201
        doc_id = r.json()["id"]

        # Première validation OK.
        r1 = client.post(
            f"/me/entreprise/documents/{doc_id}/validate",
            json={"fields": [{"key": "raison_sociale", "value": "Acme"}]},
        )
        assert r1.status_code == 200, r1.text

        # Seconde validation sans flag → 409 already_validated.
        r2 = client.post(
            f"/me/entreprise/documents/{doc_id}/validate",
            json={"fields": [{"key": "raison_sociale", "value": "Acme 2"}]},
        )
        assert r2.status_code == 409
        body = r2.json()
        assert body["detail"]["code"] == "already_validated"

    def test_404_when_doc_not_found(self, client, valid_password) -> None:
        _register_pme(client, _unique_email("v404"), valid_password)
        _provision_entreprise(client)
        r = client.post(
            f"/me/entreprise/documents/{_uuid.uuid4()}/validate",
            json={"fields": [], "propagate_to": []},
        )
        assert r.status_code == 404
        assert r.json()["detail"]["code"] == "not_found"


# ---------------------------------------------------------------------------
# Link / Unlink projet endpoints (US4 — couverture endpoints F50)
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.integration
class TestLinkUnlinkProjet:
    def test_link_then_unlink_idempotent(self, client, valid_password) -> None:
        _register_pme(client, _unique_email("lu"), valid_password)
        _provision_entreprise(client)

        r = _upload_pdf(client)
        assert r.status_code == 201
        doc_id = r.json()["id"]
        projet_id = _create_projet(client, nom="Projet de test US4")

        # Premier link → 201 + created=True.
        rl = client.post(
            f"/me/entreprise/documents/{doc_id}/link-projet",
            json={"projet_id": projet_id},
        )
        assert rl.status_code == 201, rl.text
        body = rl.json()
        assert body["document_id"] == doc_id
        assert body["projet_id"] == projet_id
        assert body["created"] is True

        # Re-link même projet → idempotent (created=False).
        rl2 = client.post(
            f"/me/entreprise/documents/{doc_id}/link-projet",
            json={"projet_id": projet_id},
        )
        # Le router renvoie 201 mais avec created=False.
        assert rl2.status_code in (200, 201)
        assert rl2.json()["created"] is False

        # Unlink → 204.
        ru = client.delete(
            f"/me/entreprise/documents/{doc_id}/link-projet/{projet_id}"
        )
        assert ru.status_code == 204

        # Unlink à nouveau → 204 idempotent.
        ru2 = client.delete(
            f"/me/entreprise/documents/{doc_id}/link-projet/{projet_id}"
        )
        assert ru2.status_code == 204

    def test_link_unknown_projet_returns_422(self, client, valid_password) -> None:
        _register_pme(client, _unique_email("luu"), valid_password)
        _provision_entreprise(client)

        r = _upload_pdf(client)
        assert r.status_code == 201
        doc_id = r.json()["id"]

        rl = client.post(
            f"/me/entreprise/documents/{doc_id}/link-projet",
            json={"projet_id": str(_uuid.uuid4())},
        )
        assert rl.status_code == 422
        assert rl.json()["detail"]["code"] == "projet_not_found"

    def test_link_doc_not_found_404(self, client, valid_password) -> None:
        _register_pme(client, _unique_email("lu404"), valid_password)
        _provision_entreprise(client)
        projet_id = _create_projet(client, nom="P quelconque")

        rl = client.post(
            f"/me/entreprise/documents/{_uuid.uuid4()}/link-projet",
            json={"projet_id": projet_id},
        )
        assert rl.status_code == 404
        assert rl.json()["detail"]["code"] == "not_found"


# ---------------------------------------------------------------------------
# Tags endpoint (US5)
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.integration
class TestUpdateTags:
    def test_patch_tags_replaces_list(self, client, valid_password) -> None:
        _register_pme(client, _unique_email("tg"), valid_password)
        _provision_entreprise(client)

        r = _upload_pdf(client)
        assert r.status_code == 201
        doc_id = r.json()["id"]

        rt = client.patch(
            f"/me/entreprise/documents/{doc_id}/tags",
            json={"tags": ["Bilan 2024", "Statuts", "Bilan 2024"]},
        )
        assert rt.status_code == 200, rt.text
        body = rt.json()
        # déduplication appliquée.
        assert body["tags"] == ["Bilan 2024", "Statuts"]

        # Le GET document doit aussi renvoyer la nouvelle liste.
        rget = client.get(f"/me/entreprise/documents/{doc_id}")
        assert rget.status_code == 200
        assert sorted(rget.json()["tags"]) == ["Bilan 2024", "Statuts"]

    def test_patch_tags_doc_not_found(self, client, valid_password) -> None:
        _register_pme(client, _unique_email("tg404"), valid_password)
        _provision_entreprise(client)

        rt = client.patch(
            f"/me/entreprise/documents/{_uuid.uuid4()}/tags",
            json={"tags": ["x"]},
        )
        assert rt.status_code == 404
        assert rt.json()["detail"]["code"] == "not_found"

    def test_patch_tags_filters_invalid(self, client, valid_password) -> None:
        _register_pme(client, _unique_email("tgf"), valid_password)
        _provision_entreprise(client)
        r = _upload_pdf(client)
        doc_id = r.json()["id"]

        rt = client.patch(
            f"/me/entreprise/documents/{doc_id}/tags",
            # Tag vide + tag > 40 chars sont filtrés silencieusement.
            json={"tags": ["", "  ", "Valide", "x" * 41]},
        )
        assert rt.status_code == 200
        assert rt.json()["tags"] == ["Valide"]


# ---------------------------------------------------------------------------
# Soft-delete with-purge endpoint (US6)
# ---------------------------------------------------------------------------


@requires_db
@pytest.mark.integration
class TestSoftDeleteWithPurge:
    def test_with_purge_endpoint_sets_purge_scheduled(
        self, client, valid_password, db_engine
    ) -> None:
        _register_pme(client, _unique_email("sd"), valid_password)
        _provision_entreprise(client)
        r = _upload_pdf(client)
        doc_id = r.json()["id"]

        rd = client.delete(
            f"/me/entreprise/documents/{doc_id}/with-purge"
        )
        assert rd.status_code == 204

        # purge_scheduled_at non NULL.
        with db_engine.connect() as c:
            c.execute(text("SET LOCAL app.is_admin = 'true'"))
            row = c.execute(
                text(
                    "SELECT deleted_at, purge_scheduled_at "
                    "FROM document_entreprise WHERE id = CAST(:id AS UUID)"
                ),
                {"id": doc_id},
            ).first()
        assert row is not None
        deleted_at, purge_scheduled_at = row
        assert deleted_at is not None
        assert purge_scheduled_at is not None

    def test_with_purge_404_when_already_deleted_or_unknown(
        self, client, valid_password
    ) -> None:
        _register_pme(client, _unique_email("sd404"), valid_password)
        _provision_entreprise(client)

        rd = client.delete(
            f"/me/entreprise/documents/{_uuid.uuid4()}/with-purge"
        )
        assert rd.status_code == 404
        assert rd.json()["detail"]["code"] == "not_found"
