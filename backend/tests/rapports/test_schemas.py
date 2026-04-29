"""F24 — Tests des schémas pydantic /me/rapports."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from app.rapports.schemas import (
    RapportCreateIn,
    RapportListOut,
    RapportOut,
)


class TestRapportCreateIn:
    def test_minimal_ok(self) -> None:
        body = RapportCreateIn(
            entity_id=uuid.uuid4(), referentiels=["ESG_MEFALI"]
        )
        assert body.entity_type == "entreprise"
        assert body.language == "fr"
        assert body.referentiels == ["ESG_MEFALI"]

    def test_referentiels_required_non_empty(self) -> None:
        with pytest.raises(ValidationError):
            RapportCreateIn(entity_id=uuid.uuid4(), referentiels=[])

    def test_referentiels_strip_and_dedupe(self) -> None:
        body = RapportCreateIn(
            entity_id=uuid.uuid4(),
            referentiels=["  A  ", "B", "A", " "],
        )
        assert body.referentiels == ["A", "B"]

    def test_invalid_entity_type(self) -> None:
        with pytest.raises(ValidationError):
            RapportCreateIn(
                entity_id=uuid.uuid4(),
                referentiels=["A"],
                entity_type="offre",  # type: ignore[arg-type]
            )

    def test_invalid_language(self) -> None:
        with pytest.raises(ValidationError):
            RapportCreateIn(
                entity_id=uuid.uuid4(),
                referentiels=["A"],
                language="es",  # type: ignore[arg-type]
            )

    def test_extra_field_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            RapportCreateIn(
                entity_id=uuid.uuid4(),
                referentiels=["A"],
                foo="bar",  # type: ignore[call-arg]
            )

    def test_max_referentiels(self) -> None:
        codes = [f"R{i}" for i in range(21)]
        with pytest.raises(ValidationError):
            RapportCreateIn(entity_id=uuid.uuid4(), referentiels=codes)


class TestRapportOut:
    def test_minimal(self) -> None:
        rid = uuid.uuid4()
        eid = uuid.uuid4()
        out = RapportOut(
            rapport_id=rid,
            entity_type="entreprise",
            entity_id=eid,
            referentiels=["ESG_MEFALI"],
            language="fr",
            file_size_bytes=1024,
            generated_at=datetime(2026, 4, 29, tzinfo=UTC),
            download_url=f"/me/rapports/{rid}/download",
        )
        assert out.file_size_bytes == 1024


class TestRapportListOut:
    def test_empty(self) -> None:
        out = RapportListOut(items=[], total=0)
        assert out.total == 0
