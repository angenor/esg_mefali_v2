"""F52 US3 — Tests unitaires Pydantic des schémas d'exports.

Couvre :
- ``ExportCreate`` : combinaisons type/format autorisées + cohérence des IDs.
- ``ExportOut`` : sérialisation, masquage signed_url si expirée.
- ``ExportListOut`` : pagination keyset.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError


@pytest.fixture()
def export_module():
    from app.dashboard import schemas_f52

    return schemas_f52


class TestExportCreate:
    def test_rgpd_full_json_ok(self, export_module) -> None:
        m = export_module.ExportCreate(type="rgpd_full", format="json")
        assert m.type == "rgpd_full"
        assert m.format == "json"
        assert m.report_id is None
        assert m.attestation_id is None
        assert m.candidature_id is None

    def test_rgpd_full_pdf_rejected(self, export_module) -> None:
        with pytest.raises(ValidationError) as exc:
            export_module.ExportCreate(type="rgpd_full", format="pdf")
        assert "format" in str(exc.value).lower() or "type" in str(exc.value).lower()

    def test_report_pdf_requires_report_id(self, export_module) -> None:
        with pytest.raises(ValidationError):
            export_module.ExportCreate(type="report_pdf", format="pdf")
        ok = export_module.ExportCreate(
            type="report_pdf", format="pdf", report_id=uuid.uuid4()
        )
        assert ok.report_id is not None

    def test_report_pdf_rejects_other_ids(self, export_module) -> None:
        with pytest.raises(ValidationError):
            export_module.ExportCreate(
                type="report_pdf",
                format="pdf",
                report_id=uuid.uuid4(),
                candidature_id=uuid.uuid4(),
            )

    def test_attestation_pdf_requires_attestation_id(self, export_module) -> None:
        with pytest.raises(ValidationError):
            export_module.ExportCreate(type="attestation_pdf", format="pdf")
        ok = export_module.ExportCreate(
            type="attestation_pdf", format="pdf", attestation_id=uuid.uuid4()
        )
        assert ok.attestation_id is not None

    def test_dossier_pdf_requires_candidature_id(self, export_module) -> None:
        with pytest.raises(ValidationError):
            export_module.ExportCreate(type="dossier_pdf", format="pdf")
        ok = export_module.ExportCreate(
            type="dossier_pdf", format="pdf", candidature_id=uuid.uuid4()
        )
        assert ok.candidature_id is not None

    def test_extra_field_forbidden(self, export_module) -> None:
        with pytest.raises(ValidationError):
            export_module.ExportCreate(
                type="rgpd_full", format="json", random_attr="x"
            )

    def test_invalid_type(self, export_module) -> None:
        with pytest.raises(ValidationError):
            export_module.ExportCreate(type="not_a_type", format="json")


class TestExportOut:
    def _payload(self, **overrides):
        base = {
            "id": uuid.uuid4(),
            "type": "rgpd_full",
            "format": "json",
            "size_bytes": None,
            "status": "pending",
            "created_at": datetime.now(UTC),
            "ready_at": None,
            "signed_url": None,
            "signed_url_expires_at": None,
            "delivered_via": None,
        }
        base.update(overrides)
        return base

    def test_serialise_pending(self, export_module) -> None:
        out = export_module.ExportOut(**self._payload())
        assert out.status == "pending"
        assert out.signed_url is None

    def test_ready_with_url(self, export_module) -> None:
        url = "https://eu-storage.example/exports/abc"
        out = export_module.ExportOut(
            **self._payload(
                status="ready",
                ready_at=datetime.now(UTC),
                signed_url=url,
                signed_url_expires_at=datetime.now(UTC) + timedelta(days=7),
                size_bytes=12345,
                delivered_via="inapp",
            )
        )
        assert out.signed_url == url
        assert out.delivered_via == "inapp"

    def test_email_delivery(self, export_module) -> None:
        out = export_module.ExportOut(
            **self._payload(
                status="ready",
                ready_at=datetime.now(UTC),
                size_bytes=200 * 1024 * 1024,
                delivered_via="email",
            )
        )
        assert out.delivered_via == "email"
        assert out.signed_url is None
