"""F21 — Tests d'integration end-to-end du seed des skills."""

from __future__ import annotations

import json
import time
import uuid
from pathlib import Path

import pytest
import yaml as _yaml
from sqlalchemy import text

from app.db import SessionLocal
from scripts.seed_skills import run_seed
from tests.integration.conftest import requires_db


def _skill_table_exists() -> bool:
    """True si la migration F19 (table ``skill``) est appliquee."""
    try:
        db = SessionLocal()
        try:
            row = db.execute(
                text(
                    "SELECT 1 FROM information_schema.tables "
                    "WHERE table_name = 'skill' LIMIT 1"
                )
            ).first()
            return row is not None
        finally:
            db.close()
    except Exception:  # noqa: BLE001
        return False


_SKILL_READY = _skill_table_exists()
requires_skill_schema = pytest.mark.skipif(
    not _SKILL_READY,
    reason="Migration F19 (table `skill`) non appliquee — `alembic upgrade head` requis.",
)

pytestmark = [pytest.mark.integration]


def _unique_suffix() -> str:
    return f"{int(time.time() * 1000)}_{uuid.uuid4().hex[:6]}"


def _write_critical(
    seeds_dir: Path, name: str, *, status_target: str = "draft"
) -> Path:
    crit = seeds_dir / "critical"
    crit.mkdir(parents=True, exist_ok=True)
    path = crit / f"{name}.yaml"
    payload = {
        "name": name,
        "version": 1,
        "domain": "diagnostic_esg",
        "language_default": "fr",
        "status_target": status_target,
        "sources": [],
        "activation_rules": {"any_of": [{"page": "/diag/*"}]},
        "tool_whitelist": ["ask_qcu", "show_radar_chart"],
        "prompt_expert": "Expert ESG. Etape 1 : extraire les elements.",
        "procedure": (
            "1. Extraire les elements E/S/G presents dans la conversation. "
            "2. Projeter sur la grille. 3. Poser des questions ciblees. "
            "4. Synthetiser sous forme de radar + summary. "
            "5. Vigilance : ne jamais quantifier sans source."
        ),
        "golden_examples": [
            {
                "input_message": f"msg{i}",
                "page_context": "/diag",
                "intent": "analyse",
                "expected_tool": "show_radar_chart",
                "expected_payload_partial": {"axes": ["E", "S", "G"]},
            }
            for i in range(5)
        ],
    }
    path.write_text(_yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _write_shell(seeds_dir: Path, name: str) -> Path:
    sh = seeds_dir / "shells"
    sh.mkdir(parents=True, exist_ok=True)
    path = sh / f"{name}.yaml"
    payload = {
        "name": name,
        "version": 1,
        "domain": "score",
        "language_default": "fr",
        "status_target": "draft",
        "sources": [],
        "activation_rules": {"any_of": [{"page": "/profil/*"}]},
        "tool_whitelist": ["ask_qcu"],
        "prompt_expert": "TODO equipe metier.",
        "procedure": "1. A definir.",
        "golden_examples": [],
    }
    path.write_text(_yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def _cleanup(names: list[str]) -> None:
    db = SessionLocal()
    try:
        for n in names:
            db.execute(text("DELETE FROM skill WHERE name = :n"), {"n": n})
        db.commit()
    finally:
        db.close()


@requires_db
@requires_skill_schema
def test_seed_inserts_skill_and_is_idempotent(tmp_path: Path) -> None:
    suffix = _unique_suffix()
    name = f"skill_seed_test_{suffix}"
    _write_critical(tmp_path, name)
    try:
        first = run_seed(seeds_dir=tmp_path)
        assert first["created"] == 1
        second = run_seed(seeds_dir=tmp_path)
        assert second["created"] == 0
        assert second["updated"] == 0
        db = SessionLocal()
        try:
            row = db.execute(
                text("SELECT version, status FROM skill WHERE name = :n"),
                {"n": name},
            ).first()
            assert row is not None
            assert row._mapping["version"] == 1
        finally:
            db.close()
    finally:
        _cleanup([name])


@requires_db
@requires_skill_schema
def test_seed_bumps_version_on_content_change(tmp_path: Path) -> None:
    suffix = _unique_suffix()
    name = f"skill_seed_bump_{suffix}"
    fixture = _write_critical(tmp_path, name)
    try:
        run_seed(seeds_dir=tmp_path)
        text_content = fixture.read_text(encoding="utf-8").replace(
            "Etape 1", "Etape 1 modifiee"
        )
        fixture.write_text(text_content, encoding="utf-8")
        second = run_seed(seeds_dir=tmp_path)
        assert second["updated"] == 1
        db = SessionLocal()
        try:
            row = db.execute(
                text("SELECT version FROM skill WHERE name = :n"), {"n": name}
            ).first()
            assert row._mapping["version"] == 2
        finally:
            db.close()
    finally:
        _cleanup([name])


@requires_db
@requires_skill_schema
def test_seed_skips_unknown_tool(tmp_path: Path) -> None:
    suffix = _unique_suffix()
    name = f"skill_seed_badtool_{suffix}"
    fixture = _write_critical(tmp_path, name)
    payload = fixture.read_text(encoding="utf-8")
    payload = payload.replace("- ask_qcu", "- tool_inexistant_xyz")
    fixture.write_text(payload, encoding="utf-8")
    try:
        summary = run_seed(seeds_dir=tmp_path)
        assert summary["skipped"] >= 1
        db = SessionLocal()
        try:
            row = db.execute(
                text("SELECT id FROM skill WHERE name = :n"), {"n": name}
            ).first()
            assert row is None
        finally:
            db.close()
    finally:
        _cleanup([name])


@requires_db
@requires_skill_schema
def test_seed_does_not_demote_published_to_draft(tmp_path: Path) -> None:
    suffix = _unique_suffix()
    name = f"skill_seed_nodemote_{suffix}"
    _write_critical(tmp_path, name, status_target="draft")
    try:
        run_seed(seeds_dir=tmp_path)
        db = SessionLocal()
        try:
            db.execute(
                text(
                    "UPDATE skill SET status = 'published', valid_from = NOW() "
                    "WHERE name = :n"
                ),
                {"n": name},
            )
            db.commit()
        finally:
            db.close()
        run_seed(seeds_dir=tmp_path)
        db = SessionLocal()
        try:
            row = db.execute(
                text("SELECT status FROM skill WHERE name = :n"), {"n": name}
            ).first()
            assert row._mapping["status"] == "published"
        finally:
            db.close()
    finally:
        _cleanup([name])


@requires_db
@requires_skill_schema
def test_seed_handles_shell_without_golden_examples(tmp_path: Path) -> None:
    suffix = _unique_suffix()
    name = f"skill_shell_test_{suffix}"
    _write_shell(tmp_path, name)
    try:
        summary = run_seed(seeds_dir=tmp_path)
        assert summary["created"] == 1
        assert summary["draft"] == 1
    finally:
        _cleanup([name])


@requires_db
@requires_skill_schema
def test_seed_summary_includes_duration(tmp_path: Path) -> None:
    # Empty dir → run rapide (sanity check < 30s, schéma JSON sérialisable).
    summary = run_seed(seeds_dir=tmp_path)
    assert "duration_ms" in summary
    assert summary["duration_ms"] < 30_000
    json.dumps(summary)
