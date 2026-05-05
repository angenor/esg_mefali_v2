"""F52 — Tests unitaires des schémas Pydantic v2 ``ReadAllRequest`` /
``ReadAllResponse`` et de la query list (avec ``kinds[]``)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from app.notifications.schemas_f52 import (
    NotificationListQueryF52,
    ReadAllRequest,
    ReadAllResponse,
)


class TestReadAllRequest:
    def test_kinds_optional(self) -> None:
        m = ReadAllRequest()
        assert m.kinds is None

    def test_kinds_valid_list(self) -> None:
        m = ReadAllRequest(kinds=["deadline_j_minus_30", "offre_recommandee"])
        assert m.kinds == ["deadline_j_minus_30", "offre_recommandee"]

    def test_rejects_unknown_kind(self) -> None:
        with pytest.raises(ValidationError):
            ReadAllRequest(kinds=["NOT_A_KIND"])  # type: ignore[list-item]

    def test_extra_forbidden(self) -> None:
        with pytest.raises(ValidationError):
            ReadAllRequest(extra_field="oops")  # type: ignore[call-arg]


class TestReadAllResponse:
    def test_basic(self) -> None:
        m = ReadAllResponse(updated_count=5, unread_count_after=0)
        assert m.updated_count == 5
        assert m.unread_count_after == 0

    def test_negatives_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ReadAllResponse(updated_count=-1, unread_count_after=0)


class TestListQueryF52:
    def test_defaults(self) -> None:
        q = NotificationListQueryF52()
        assert q.unread_only is False
        assert q.kind == []
        assert q.limit == 20

    def test_kind_repeatable(self) -> None:
        q = NotificationListQueryF52(
            kind=["deadline_j_minus_7", "candidature_inactive"]
        )
        assert len(q.kind) == 2

    def test_limit_bounds(self) -> None:
        with pytest.raises(ValidationError):
            NotificationListQueryF52(limit=0)
        with pytest.raises(ValidationError):
            NotificationListQueryF52(limit=200)
