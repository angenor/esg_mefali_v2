"""F24 — Tests unitaires des helpers du service (sans DB)."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime

from app.rapports.service import (
    _collect_source_ids,
    _serialize_snapshot,
    _split_points_lacunes,
    _storage_path,
)


class TestSplitPointsLacunes:
    def test_high_contribution_is_point_fort(self) -> None:
        detail = {
            "indicateurs_couverts": [
                {
                    "indicateur_code": "X",
                    "pillar": "E",
                    "contribution": 60.0,
                },
                {
                    "indicateur_code": "Y",
                    "pillar": "S",
                    "contribution": 10.0,
                },
            ],
            "indicateurs_manquants": [],
        }
        points, lacunes = _split_points_lacunes(detail)
        assert len(points) == 1
        assert points[0].code == "X"
        assert lacunes == []

    def test_missing_become_lacunes(self) -> None:
        detail = {
            "indicateurs_couverts": [],
            "indicateurs_manquants": [
                {
                    "indicateur_code": "Z",
                    "pillar": "G",
                    "reason": "value_absent",
                },
            ],
        }
        points, lacunes = _split_points_lacunes(detail)
        assert points == []
        assert len(lacunes) == 1
        assert lacunes[0].reason == "value_absent"

    def test_invalid_contribution_skipped(self) -> None:
        detail = {
            "indicateurs_couverts": [
                {
                    "indicateur_code": "X",
                    "pillar": "E",
                    "contribution": "abc",
                },
            ],
            "indicateurs_manquants": [],
        }
        points, lacunes = _split_points_lacunes(detail)
        assert points == []


class TestCollectSourceIds:
    def test_dedupe_across_details(self) -> None:
        sid = str(uuid.uuid4())
        details = [
            {"sources_used": [sid, sid]},
            {"sources_used": [sid]},
        ]
        out = _collect_source_ids(details)
        assert len(out) == 1
        assert str(out[0]) == sid

    def test_invalid_uuid_skipped(self) -> None:
        details = [{"sources_used": ["not-a-uuid"]}]
        assert _collect_source_ids(details) == []

    def test_empty(self) -> None:
        assert _collect_source_ids([]) == []


class TestSerializeSnapshot:
    def test_serializes_datetime(self) -> None:
        details = [
            {
                "referentiel_code": "ESG_MEFALI",
                "referentiel_version": 1,
                "score_global": 72.5,
                "scores_by_pillar": {"E": 70},
                "coverage_ratio": 0.8,
                "computed_at": datetime(2026, 4, 29, tzinfo=UTC),
            }
        ]
        snap = _serialize_snapshot(details)
        assert "sections" in snap
        assert snap["sections"][0]["referentiel_code"] == "ESG_MEFALI"
        assert isinstance(snap["sections"][0]["computed_at"], str)
        assert snap["sections"][0]["computed_at"].startswith("2026-04-29")

    def test_handles_none_values(self) -> None:
        details = [
            {
                "referentiel_code": "X",
                "referentiel_version": 0,
                "score_global": None,
                "scores_by_pillar": {},
                "coverage_ratio": None,
                "computed_at": None,
            }
        ]
        snap = _serialize_snapshot(details)
        assert snap["sections"][0]["score_global"] is None


class TestStoragePath:
    def test_path_layout(self) -> None:
        aid = uuid.UUID("00000000-0000-0000-0000-00000000000a")
        rid = uuid.UUID("00000000-0000-0000-0000-00000000000b")
        path = _storage_path(aid, rid)
        assert str(aid) in str(path)
        assert str(rid) in str(path)
        assert str(path).endswith(".pdf")
