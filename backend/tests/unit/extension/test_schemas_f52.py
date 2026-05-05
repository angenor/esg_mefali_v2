"""F52 US4 — Tests unitaires des schémas Pydantic du sidepanel & ping."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from pydantic import ValidationError


@pytest.fixture()
def schemas_f52():
    from app.extension import schemas_f52

    return schemas_f52


class TestExtensionPingIn:
    def test_valid_semver(self, schemas_f52) -> None:
        m = schemas_f52.ExtensionPingIn(
            extension_version="0.4.2",
            user_agent_summary="Chrome/124.0 macOS",
        )
        assert m.extension_version == "0.4.2"

    def test_invalid_semver(self, schemas_f52) -> None:
        with pytest.raises(ValidationError):
            schemas_f52.ExtensionPingIn(
                extension_version="not-semver",
                user_agent_summary="Chrome",
            )

    def test_user_agent_summary_too_long(self, schemas_f52) -> None:
        with pytest.raises(ValidationError):
            schemas_f52.ExtensionPingIn(
                extension_version="1.0.0",
                user_agent_summary="X" * 256,
            )

    def test_extra_field_forbidden(self, schemas_f52) -> None:
        with pytest.raises(ValidationError):
            schemas_f52.ExtensionPingIn(
                extension_version="1.0.0",
                user_agent_summary="x",
                rogue_field="x",
            )


class TestSidepanelContextOut:
    def test_minimal_payload(self, schemas_f52) -> None:
        out = schemas_f52.SidepanelContextOut(
            matched_offer_ids=[],
            active_candidatures=[],
            recommended_offers=[],
        )
        assert out.matched_offer_ids == []

    def test_with_candidatures(self, schemas_f52) -> None:
        cid = uuid.uuid4()
        item = schemas_f52.SidepanelCandidatureItem(
            id=cid,
            offer_label="BOAD — Ligne verte",
            deadline_at=datetime.now(UTC) + timedelta(days=10),
            completion_pct=62,
            resume_url="https://app.esg-mefali.example/candidatures/" + str(cid),
        )
        out = schemas_f52.SidepanelContextOut(
            matched_offer_ids=[cid],
            active_candidatures=[item],
            recommended_offers=[],
        )
        assert out.active_candidatures[0].id == cid

    def test_completion_pct_bounds(self, schemas_f52) -> None:
        cid = uuid.uuid4()
        with pytest.raises(ValidationError):
            schemas_f52.SidepanelCandidatureItem(
                id=cid,
                offer_label="x",
                deadline_at=datetime.now(UTC),
                completion_pct=150,
                resume_url="https://app.example/x",
            )


class TestSidepanelOfferItem:
    def test_match_score_range(self, schemas_f52) -> None:
        oid = uuid.uuid4()
        ok = schemas_f52.SidepanelOfferItem(
            id=oid,
            label="AFD — Climat & Genre",
            match_score=0.81,
            matching_url="https://app.example/matching?offer=" + str(oid),
        )
        assert 0.0 <= ok.match_score <= 1.0

    def test_match_score_invalid(self, schemas_f52) -> None:
        oid = uuid.uuid4()
        with pytest.raises(ValidationError):
            schemas_f52.SidepanelOfferItem(
                id=oid,
                label="x",
                match_score=2.0,
                matching_url="https://x.example",
            )
