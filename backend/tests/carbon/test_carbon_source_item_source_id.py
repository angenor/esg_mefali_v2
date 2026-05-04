"""F47 T008 — Tests rétrocompat de l'extension CarbonSourceItem.source_id."""

from __future__ import annotations

from decimal import Decimal
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.carbon.schemas import CarbonSourceItem


class TestCarbonSourceItemSourceId:
    def test_source_id_default_none_accepted(self):
        item = CarbonSourceItem(code="ELEC_CIV", quantity=Decimal("100"))
        assert item.source_id is None
        assert item.country is None

    def test_source_id_uuid_accepted(self):
        sid = uuid4()
        item = CarbonSourceItem(
            code="ELEC_CIV", quantity=Decimal("100"), source_id=sid
        )
        assert item.source_id == sid

    def test_source_id_string_uuid_accepted(self):
        sid = str(uuid4())
        item = CarbonSourceItem(
            code="ELEC_CIV", quantity=Decimal("100"), source_id=sid
        )
        assert str(item.source_id) == sid

    def test_source_id_invalid_raises(self):
        with pytest.raises(ValidationError):
            CarbonSourceItem(
                code="ELEC_CIV", quantity=Decimal("100"), source_id="not-a-uuid"
            )

    def test_extra_field_rejected(self):
        with pytest.raises(ValidationError):
            CarbonSourceItem(  # type: ignore[call-arg]
                code="ELEC_CIV",
                quantity=Decimal("100"),
                unknown_field="x",
            )

    def test_negative_quantity_rejected(self):
        with pytest.raises(ValidationError):
            CarbonSourceItem(code="ELEC_CIV", quantity=Decimal("-1"))
