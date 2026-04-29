"""F21 — Tests unitaires des helpers du seed des skills."""

from __future__ import annotations

from pathlib import Path

import pytest

from app.skills.seed_helpers import (
    GOLDEN_MIN_COUNT,
    PROCEDURE_MIN_CHARS_CRITICAL,
    PROMPT_MAX_CHARS,
    content_hash,
    known_tools,
    load_skill_yaml,
    should_publish,
    validate_fixture_shape,
    validate_golden_examples,
)


def _valid_payload() -> dict:
    return {
        "name": "skill_test",
        "domain": "diagnostic_esg",
        "prompt_expert": "Tu es un expert ESG. Etape 1 : extraire les elements.",
        "tool_whitelist": ["ask_qcu", "show_radar_chart"],
        "activation_rules": {
            "any": [{"field": "page", "op": "eq", "value": "/diag"}]
        },
        "procedure": "1. Extraire E.\n2. Completer S.\n3. Synthetiser G.",
        "language_default": "fr",
        "status_target": "draft",
    }


# -------------------------------- content_hash -------------------------------


def test_content_hash_stable_for_identical_payload() -> None:
    p = _valid_payload()
    assert content_hash(p) == content_hash(p)


def test_content_hash_changes_when_prompt_changes() -> None:
    p = _valid_payload()
    h1 = content_hash(p)
    p["prompt_expert"] = "Modifie."
    h2 = content_hash(p)
    assert h1 != h2


def test_content_hash_changes_when_whitelist_changes() -> None:
    p = _valid_payload()
    h1 = content_hash(p)
    p["tool_whitelist"] = [*p["tool_whitelist"], "show_kpi_card"]
    h2 = content_hash(p)
    assert h1 != h2


def test_content_hash_ignores_non_semantic_fields() -> None:
    p = _valid_payload()
    h1 = content_hash(p)
    p["name"] = "renommee"
    p["domain"] = "autre"
    p["status_target"] = "published"
    h2 = content_hash(p)
    assert h1 == h2


def test_content_hash_insensitive_to_key_order() -> None:
    p1 = _valid_payload()
    p2 = {k: p1[k] for k in reversed(list(p1.keys()))}
    assert content_hash(p1) == content_hash(p2)


# -------------------------------- load_skill_yaml ----------------------------


def test_load_skill_yaml_ok(tmp_path: Path) -> None:
    f = tmp_path / "ok.yaml"
    f.write_text("name: foo\ndomain: bar\n", encoding="utf-8")
    data = load_skill_yaml(f)
    assert data["name"] == "foo"


def test_load_skill_yaml_rejects_non_dict_root(tmp_path: Path) -> None:
    f = tmp_path / "ko.yaml"
    f.write_text("- a\n- b\n", encoding="utf-8")
    with pytest.raises(ValueError):
        load_skill_yaml(f)


# -------------------------------- validate_fixture_shape ---------------------


def test_validate_shape_ok_for_valid_payload() -> None:
    assert validate_fixture_shape(_valid_payload()) == []


def test_validate_shape_detects_missing_field() -> None:
    p = _valid_payload()
    p.pop("prompt_expert")
    errors = validate_fixture_shape(p)
    assert any("prompt_expert" in e for e in errors)


def test_validate_shape_rejects_invalid_tool_whitelist_type() -> None:
    p = _valid_payload()
    p["tool_whitelist"] = "ask_qcu"
    errors = validate_fixture_shape(p)
    assert any("tool_whitelist" in e for e in errors)


def test_validate_shape_rejects_too_long_prompt() -> None:
    p = _valid_payload()
    p["prompt_expert"] = "A" * (PROMPT_MAX_CHARS + 1)
    errors = validate_fixture_shape(p)
    assert any("trop long" in e for e in errors)


def test_validate_shape_requires_french_language() -> None:
    p = _valid_payload()
    p["language_default"] = "en"
    errors = validate_fixture_shape(p)
    assert any("'fr'" in e for e in errors)


def test_validate_shape_rejects_invalid_status_target() -> None:
    p = _valid_payload()
    p["status_target"] = "deprecated"
    errors = validate_fixture_shape(p)
    assert any("status_target" in e for e in errors)


def test_validate_shape_critical_requires_procedure() -> None:
    p = _valid_payload()
    p["procedure"] = "trop court"
    errors = validate_fixture_shape(p, is_critical=True)
    assert any("procedure" in e for e in errors)


def test_validate_shape_critical_accepts_long_procedure() -> None:
    p = _valid_payload()
    p["procedure"] = "Etape :\n" + "x" * (PROCEDURE_MIN_CHARS_CRITICAL + 10)
    errors = validate_fixture_shape(p, is_critical=True)
    assert errors == []


# -------------------------------- validate_golden_examples -------------------


def _ex(expected_tool: str = "ask_qcu", intent: str = "analyse") -> dict:
    return {
        "input_message": "msg",
        "page_context": "/diag",
        "intent": intent,
        "expected_tool": expected_tool,
        "expected_payload_partial": {"k": "v"},
    }


def test_validate_golden_ok_with_5_examples() -> None:
    examples = [_ex() for _ in range(GOLDEN_MIN_COUNT)]
    assert validate_golden_examples(examples, ["ask_qcu"]) == []


def test_validate_golden_rejects_below_minimum() -> None:
    examples = [_ex() for _ in range(GOLDEN_MIN_COUNT - 1)]
    errors = validate_golden_examples(examples, ["ask_qcu"])
    assert any("requis" in e for e in errors)


def test_validate_golden_rejects_tool_outside_whitelist() -> None:
    examples = [_ex(expected_tool="bad_tool") for _ in range(GOLDEN_MIN_COUNT)]
    errors = validate_golden_examples(examples, ["ask_qcu"])
    assert any("absent de tool_whitelist" in e for e in errors)


def test_validate_golden_rejects_invalid_intent() -> None:
    examples = [_ex(intent="lol") for _ in range(GOLDEN_MIN_COUNT)]
    errors = validate_golden_examples(examples, ["ask_qcu"])
    assert any("intent" in e for e in errors)


def test_validate_golden_rejects_non_list() -> None:
    errors = validate_golden_examples({"oops": True}, ["ask_qcu"])  # type: ignore[arg-type]
    assert errors


def test_validate_golden_rejects_missing_required() -> None:
    bad = [{"input_message": "x"} for _ in range(GOLDEN_MIN_COUNT)]
    errors = validate_golden_examples(bad, ["ask_qcu"])
    assert any("page_context" in e for e in errors)


# -------------------------------- should_publish -----------------------------


def test_should_publish_skip_on_unknown_tools() -> None:
    status, reasons = should_publish(
        status_target="published",
        missing_sources=[],
        non_verified_publishers=[],
        unknown_tools=["bad_tool"],
    )
    assert status == "skip"
    assert any("Tools inconnus" in r for r in reasons)


def test_should_publish_draft_when_target_is_draft() -> None:
    status, reasons = should_publish(
        status_target="draft",
        missing_sources=[],
        non_verified_publishers=[],
        unknown_tools=[],
    )
    assert status == "draft"
    assert reasons == []


def test_should_publish_published_when_all_ok() -> None:
    status, reasons = should_publish(
        status_target="published",
        missing_sources=[],
        non_verified_publishers=[],
        unknown_tools=[],
    )
    assert status == "published"
    assert reasons == []


def test_should_publish_draft_when_sources_missing() -> None:
    status, reasons = should_publish(
        status_target="published",
        missing_sources=[{"publisher": "X", "title_match": "Y"}],
        non_verified_publishers=[],
        unknown_tools=[],
    )
    assert status == "draft"
    assert any("introuvable" in r for r in reasons)


def test_should_publish_draft_when_sources_not_verified() -> None:
    status, reasons = should_publish(
        status_target="published",
        missing_sources=[],
        non_verified_publishers=["GCF"],
        unknown_tools=[],
    )
    assert status == "draft"
    assert any("non verified" in r for r in reasons)


# -------------------------------- known_tools --------------------------------


def test_known_tools_returns_non_empty_set() -> None:
    tools = known_tools()
    assert isinstance(tools, set)
    assert len(tools) > 0
    assert "ask_qcu" in tools or "respond_user" in tools


# -------------------------------- resolve_sources ----------------------------


class _FakeRow:
    def __init__(self, mapping: dict) -> None:
        self._mapping = mapping


class _FakeResult:
    def __init__(self, row: _FakeRow | None) -> None:
        self._row = row

    def first(self) -> _FakeRow | None:
        return self._row


class _FakeSession:
    def __init__(self, rows: list[_FakeRow | None]) -> None:
        self._rows = list(rows)

    def execute(self, _stmt, _params):  # noqa: ANN001
        return _FakeResult(self._rows.pop(0))


def test_resolve_sources_empty_returns_empty() -> None:
    from app.skills.seed_helpers import resolve_sources

    db = _FakeSession([])
    found, missing, nv = resolve_sources(db, [])  # type: ignore[arg-type]
    assert found == [] and missing == [] and nv == []


def test_resolve_sources_collects_found_and_missing() -> None:
    from uuid import uuid4

    from app.skills.seed_helpers import resolve_sources

    sid = uuid4()
    rows = [
        _FakeRow({"id": sid, "verification_status": "verified"}),
        None,  # second ref not found
        _FakeRow({"id": uuid4(), "verification_status": "pending"}),
    ]
    db = _FakeSession(rows)
    refs = [
        {"publisher": "GCF", "title_match": "Framework"},
        {"publisher": "X", "title_match": "Y"},
        {"publisher": "BOAD", "title_match": "Politique"},
    ]
    found, missing, nv = resolve_sources(db, refs)  # type: ignore[arg-type]
    assert sid in found
    assert {"publisher": "X", "title_match": "Y"} in missing
    assert "BOAD" in nv


def test_resolve_sources_marks_incomplete_ref_as_missing() -> None:
    from app.skills.seed_helpers import resolve_sources

    db = _FakeSession([])
    refs = [{"publisher": "GCF"}]  # no title_match
    found, missing, nv = resolve_sources(db, refs)  # type: ignore[arg-type]
    assert found == []
    assert missing == [{"publisher": "GCF"}]
    assert nv == []
