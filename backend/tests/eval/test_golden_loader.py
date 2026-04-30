"""F35 — Tests pour ``golden_loader``."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.eval.golden_loader import GoldenCase, load_cases


def _seed_path() -> Path:
    return Path(__file__).resolve().parents[1] / "llm_eval" / "golden_seed.json"


@pytest.mark.unit
def test_load_seed_returns_cases() -> None:
    cases = load_cases(_seed_path())
    assert len(cases) >= 10
    assert all(isinstance(c, GoldenCase) for c in cases)
    ids = {c.id for c in cases}
    assert "qcu-forme-juridique" in ids
    assert "fallback-aide-libre" in ids


@pytest.mark.unit
def test_filter_tags_intersection() -> None:
    cases = load_cases(_seed_path(), filter_tags=["forme_juridique"])
    assert len(cases) >= 1
    assert all("forme_juridique" in c.tags for c in cases)


@pytest.mark.unit
def test_filter_tags_no_match() -> None:
    cases = load_cases(_seed_path(), filter_tags=["does-not-exist"])
    assert cases == []


@pytest.mark.unit
def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        load_cases(tmp_path / "missing.json")


@pytest.mark.unit
def test_invalid_json_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text("{not valid json", encoding="utf-8")
    with pytest.raises(ValueError, match="invalid JSON"):
        load_cases(p)


@pytest.mark.unit
def test_top_level_not_a_list_raises(tmp_path: Path) -> None:
    p = tmp_path / "obj.json"
    p.write_text(json.dumps({"foo": "bar"}), encoding="utf-8")
    with pytest.raises(ValueError, match="must be a list"):
        load_cases(p)


@pytest.mark.unit
def test_missing_required_field_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(json.dumps([{"id": "x"}]), encoding="utf-8")
    with pytest.raises(ValueError, match="missing"):
        load_cases(p)


@pytest.mark.unit
def test_missing_expected_tool_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(
        json.dumps(
            [
                {
                    "id": "x",
                    "description": "d",
                    "user_message": "m",
                    "expected": {"payload_partial": {}},
                }
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="expected.tool"):
        load_cases(p)


@pytest.mark.unit
def test_invalid_context_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(
        json.dumps(
            [
                {
                    "id": "x",
                    "description": "d",
                    "user_message": "m",
                    "context": "not-an-object",
                    "expected": {"tool": "ask_qcu"},
                }
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="context"):
        load_cases(p)


@pytest.mark.unit
def test_invalid_tags_raises(tmp_path: Path) -> None:
    p = tmp_path / "bad.json"
    p.write_text(
        json.dumps(
            [
                {
                    "id": "x",
                    "description": "d",
                    "user_message": "m",
                    "expected": {"tool": "ask_qcu"},
                    "tags": "not-a-list",
                }
            ]
        ),
        encoding="utf-8",
    )
    with pytest.raises(ValueError, match="tags"):
        load_cases(p)


@pytest.mark.unit
def test_case_immutability() -> None:
    cases = load_cases(_seed_path())
    c = cases[0]
    with pytest.raises((AttributeError, Exception)):
        c.id = "modified"  # type: ignore[misc]
