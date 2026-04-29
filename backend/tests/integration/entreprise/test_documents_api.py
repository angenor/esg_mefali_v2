"""F22 - Tests integration HTTP /me/entreprise/documents.

Suit le pattern F11/F12 : enregistre une PME, provisionne son entreprise via
GET /me/entreprise, puis exerce les endpoints upload/list/get/download/delete.
Auto-skip si Postgres indisponible (cf. tests/integration/conftest.py).
"""

from __future__ import annotations

import io
import time
import uuid as _uuid

from tests.integration.conftest import requires_db

PDF_NATIVE = (
    b"%PDF-1.4\n"
    b"1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 612 792]"
    b"/Contents 4 0 R/Resources<</Font<</F1 5 0 R>>>>>>endobj\n"
    b"4 0 obj<</Length 55>>stream\n"
    b"BT\n/F1 18 Tf\n72 720 Td\n(F22 statuts SARL) Tj\nET\n"
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


def _upload(
    client,
    *,
    mime: str = "application/pdf",
    data: bytes = PDF_NATIVE,
    doc_type: str = "statuts",
    filename: str = "statuts.pdf",
):
    return client.post(
        "/me/entreprise/documents",
        files={"file": (filename, io.BytesIO(data), mime)},
        data={"type": doc_type},
    )


@requires_db
class TestUpload:
    def test_post_upload_201_pdf_native(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        _provision_entreprise(client)
        r = _upload(client)
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["mime_type"] == "application/pdf"
        assert body["type"] == "statuts"
        assert body["ocr_status"] == "done"
        assert body["size_bytes"] == len(PDF_NATIVE)

    def test_post_upload_415_bad_mime(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        _provision_entreprise(client)
        r = _upload(
            client,
            mime="application/x-msdownload",
            data=b"MZ\x90",
            filename="x.exe",
        )
        assert r.status_code == 415, r.text
        assert r.json()["detail"]["code"] == "mime_not_allowed"

    def test_post_upload_422_bad_doc_type(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        _provision_entreprise(client)
        r = _upload(client, doc_type="inconnu")
        assert r.status_code == 422, r.text
        assert r.json()["detail"]["code"] == "doc_type_invalid"

    def test_post_jpg_returns_deferred(
        self, client, unique_email, valid_password
    ) -> None:
        _register_pme(client, unique_email, valid_password)
        _provision_entreprise(client)
        r = _upload(
            client,
            mime="image/jpeg",
            data=b"\xff\xd8\xff\xe0\x00\x10JFIF\x00",
            doc_type="autre",
            filename="photo.jpg",
        )
        assert r.status_code == 201, r.text
        body = r.json()
        assert body["ocr_status"] == "deferred"
        assert body["ocr_error"] == "mvp_image_unsupported"


@requires_db
class TestListDownloadDelete:
    def test_full_cycle(self, client, unique_email, valid_password) -> None:
        _register_pme(client, unique_email, valid_password)
        _provision_entreprise(client)

        r1 = _upload(client, doc_type="statuts", filename="s.pdf")
        assert r1.status_code == 201
        r2 = _upload(client, doc_type="contrat", filename="c.pdf")
        assert r2.status_code == 201
        doc1_id = r1.json()["id"]
        doc2_id = r2.json()["id"]

        rl = client.get("/me/entreprise/documents")
        assert rl.status_code == 200
        items = rl.json()["items"]
        assert len(items) >= 2
        ids = {it["id"] for it in items}
        assert {doc1_id, doc2_id} <= ids

        rd = client.get(f"/me/entreprise/documents/{doc1_id}")
        assert rd.status_code == 200
        assert rd.json()["id"] == doc1_id
        assert rd.json()["ocr_status"] == "done"

        rdl = client.get(f"/me/entreprise/documents/{doc1_id}/download")
        assert rdl.status_code == 200
        assert rdl.content == PDF_NATIVE
        assert rdl.headers["content-type"].startswith("application/pdf")

        rdel = client.delete(f"/me/entreprise/documents/{doc1_id}")
        assert rdel.status_code == 204

        rl2 = client.get("/me/entreprise/documents")
        assert rl2.status_code == 200
        ids2 = {it["id"] for it in rl2.json()["items"]}
        assert doc1_id not in ids2

        rdet = client.get(f"/me/entreprise/documents/{doc1_id}")
        assert rdet.status_code == 404


@requires_db
class TestCrossTenant:
    def test_user_b_cannot_access_user_a_doc(
        self, client, valid_password
    ) -> None:
        email_a = f"a_{int(time.time()*1000)}_{_uuid.uuid4().hex[:6]}@ex.com"
        _register_pme(client, email_a, valid_password)
        _provision_entreprise(client)
        ra = _upload(client)
        assert ra.status_code == 201
        doc_a_id = ra.json()["id"]

        client.cookies.clear()
        client.headers.pop("X-CSRF-Token", None)
        email_b = f"b_{int(time.time()*1000)}_{_uuid.uuid4().hex[:6]}@ex.com"
        _register_pme(client, email_b, valid_password)
        _provision_entreprise(client)

        rget = client.get(f"/me/entreprise/documents/{doc_a_id}")
        assert rget.status_code == 404
        rdl = client.get(f"/me/entreprise/documents/{doc_a_id}/download")
        assert rdl.status_code == 404
        rdel = client.delete(f"/me/entreprise/documents/{doc_a_id}")
        assert rdel.status_code == 404
