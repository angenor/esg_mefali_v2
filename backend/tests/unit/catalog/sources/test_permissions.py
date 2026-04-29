"""F07 — Tests unitaires des permissions Source.

- ``assert_can_verify`` : un admin ne peut pas auto-valider sa propre source
  (lève HTTPException 409).
"""

from __future__ import annotations

import uuid

import pytest
from fastapi import HTTPException

from app.catalog.sources.permissions import assert_can_verify


def test_self_verify_blocked():
    actor_id = uuid.uuid4()
    source = {"id": uuid.uuid4(), "captured_by": actor_id}
    with pytest.raises(HTTPException) as exc:
        assert_can_verify(source, actor_id)
    assert exc.value.status_code == 409
    detail = exc.value.detail
    assert isinstance(detail, dict)
    assert detail.get("code") == "self_verification_forbidden"


def test_cross_admin_verify_allowed():
    captured_by = uuid.uuid4()
    actor_id = uuid.uuid4()  # autre admin
    source = {"id": uuid.uuid4(), "captured_by": captured_by}
    # ne lève pas
    assert_can_verify(source, actor_id) is None  # noqa: B015
