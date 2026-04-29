"""Tests F19 — snapshot interface."""

from __future__ import annotations

import uuid

import pytest

from app.skills.snapshot import SkillSnapshot, snapshot_skill_version


def test_snapshot_basic() -> None:
    tid, sid = uuid.uuid4(), uuid.uuid4()
    snap = snapshot_skill_version(tid, sid, 1)
    assert isinstance(snap, SkillSnapshot)
    assert snap.thread_id == tid
    assert snap.skill_id == sid
    assert snap.version == 1


def test_snapshot_accepts_str_uuids() -> None:
    tid, sid = str(uuid.uuid4()), str(uuid.uuid4())
    snap = snapshot_skill_version(tid, sid, 3)
    assert snap.version == 3


def test_snapshot_rejects_invalid_version() -> None:
    with pytest.raises(ValueError):
        snapshot_skill_version(uuid.uuid4(), uuid.uuid4(), 0)


def test_snapshot_is_immutable() -> None:
    snap = snapshot_skill_version(uuid.uuid4(), uuid.uuid4(), 1)
    with pytest.raises(Exception):  # noqa: B017,PT011
        snap.version = 99  # type: ignore[misc]
