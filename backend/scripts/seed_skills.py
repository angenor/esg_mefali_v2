"""F21 — Script de seed des skills MVP.

Usage::

    python -m scripts.seed_skills [--force] [--dry-run]
                                  [--only NAME ...] [--seeds-dir PATH]

Idempotent : ré-exécution sans changement → pas de bump de version.
"""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db import SessionLocal
from app.skills.seed_helpers import (
    content_hash,
    known_tools,
    load_skill_yaml,
    resolve_sources,
    should_publish,
    validate_fixture_shape,
    validate_golden_examples,
)

logger = logging.getLogger("seed_skills")

DEFAULT_SEEDS_DIR = Path(__file__).resolve().parent / "seeds" / "skills"


def _setup_logging(verbose: bool = False) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level, format="%(levelname)s [%(name)s] %(message)s", force=True
    )


def _iter_fixtures(seeds_dir: Path) -> list[tuple[Path, bool]]:
    """Retourne ``[(path, is_critical), ...]`` triés (critiques en tête)."""
    out: list[tuple[Path, bool]] = []
    crit_dir = seeds_dir / "critical"
    shells_dir = seeds_dir / "shells"
    if crit_dir.exists():
        out.extend((p, True) for p in sorted(crit_dir.glob("*.yaml")))
    if shells_dir.exists():
        out.extend((p, False) for p in sorted(shells_dir.glob("*.yaml")))
    return out


def _fetch_existing(db: Session, name: str) -> dict[str, Any] | None:
    row = db.execute(
        text("SELECT * FROM skill WHERE name = :name LIMIT 1"),
        {"name": name},
    ).first()
    return dict(row._mapping) if row else None


def _payload_from_db(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "prompt_expert": row.get("prompt_expert", ""),
        "activation_rules": row.get("activation_rules") or {},
        "tool_whitelist": list(row.get("tool_whitelist") or []),
        "procedure": row.get("procedure", ""),
    }


def _payload_from_fixture(data: dict[str, Any]) -> dict[str, Any]:
    return {
        "prompt_expert": data.get("prompt_expert", ""),
        "activation_rules": data.get("activation_rules") or {},
        "tool_whitelist": list(data.get("tool_whitelist") or []),
        "procedure": data.get("procedure", ""),
    }


def _link_sources(
    db: Session, skill_id: uuid.UUID | str, source_ids: list[uuid.UUID]
) -> None:
    db.execute(
        text("DELETE FROM skill_source WHERE skill_id = CAST(:sid AS UUID)"),
        {"sid": str(skill_id)},
    )
    if not source_ids:
        return
    now = datetime.now(UTC)
    for src_id in source_ids:
        db.execute(
            text(
                "INSERT INTO skill_source (skill_id, source_id, created_at) "
                "VALUES (CAST(:sid AS UUID), CAST(:src AS UUID), :now) "
                "ON CONFLICT DO NOTHING"
            ),
            {"sid": str(skill_id), "src": str(src_id), "now": now},
        )


def _insert_skill(
    db: Session, *, data: dict[str, Any], final_status: str, version: int
) -> uuid.UUID:
    skill_id = uuid.uuid4()
    now = datetime.now(UTC)
    db.execute(
        text(
            """
            INSERT INTO skill (
                id, name, version, domain, prompt_expert, procedure,
                tool_whitelist, activation_rules, golden_examples, status,
                valid_from, created_at, updated_at
            ) VALUES (
                CAST(:id AS UUID), :name, :version, :domain, :prompt_expert,
                :procedure, CAST(:tool_whitelist AS TEXT[]),
                CAST(:activation_rules AS JSONB),
                CAST(:golden_examples AS JSONB), :status,
                :valid_from, :now, :now
            )
            """
        ),
        {
            "id": str(skill_id),
            "name": data["name"],
            "version": version,
            "domain": data["domain"],
            "prompt_expert": data["prompt_expert"],
            "procedure": data.get("procedure", ""),
            "tool_whitelist": list(data.get("tool_whitelist") or []),
            "activation_rules": json.dumps(data.get("activation_rules") or {}),
            "golden_examples": json.dumps(data.get("golden_examples") or []),
            "status": final_status,
            "valid_from": now if final_status == "published" else None,
            "now": now,
        },
    )
    return skill_id


def _update_skill(
    db: Session,
    *,
    existing: dict[str, Any],
    data: dict[str, Any],
    final_status: str,
    new_version: int,
) -> None:
    now = datetime.now(UTC)
    valid_from = existing.get("valid_from")
    if final_status == "published" and not valid_from:
        valid_from = now
    db.execute(
        text(
            """
            UPDATE skill SET
                version = :version,
                domain = :domain,
                prompt_expert = :prompt_expert,
                procedure = :procedure,
                tool_whitelist = CAST(:tool_whitelist AS TEXT[]),
                activation_rules = CAST(:activation_rules AS JSONB),
                golden_examples = CAST(:golden_examples AS JSONB),
                status = :status,
                valid_from = :valid_from,
                updated_at = :now
            WHERE id = :id
            """
        ),
        {
            "id": str(existing["id"]),
            "version": new_version,
            "domain": data["domain"],
            "prompt_expert": data["prompt_expert"],
            "procedure": data.get("procedure", ""),
            "tool_whitelist": list(data.get("tool_whitelist") or []),
            "activation_rules": json.dumps(data.get("activation_rules") or {}),
            "golden_examples": json.dumps(data.get("golden_examples") or []),
            "status": final_status,
            "valid_from": valid_from,
            "now": now,
        },
    )


def _process_fixture(
    db: Session,
    *,
    path: Path,
    is_critical: bool,
    force: bool,
    dry_run: bool,
    available_tools: set[str],
    summary: dict[str, int],
) -> None:
    data = load_skill_yaml(path)
    name = data.get("name", "<unnamed>")

    shape_errors = validate_fixture_shape(data, is_critical=is_critical)
    if shape_errors:
        for e in shape_errors:
            logger.error("[%s] fixture invalide : %s", name, e)
        summary["skipped"] += 1
        summary["errors"] += 1
        return

    whitelist = list(data.get("tool_whitelist") or [])
    unknown = [t for t in whitelist if t not in available_tools]

    golden = data.get("golden_examples") or []
    if is_critical:
        golden_errors = validate_golden_examples(golden, whitelist)
        if golden_errors:
            for e in golden_errors:
                logger.error("[%s] golden_examples invalides : %s", name, e)
            summary["skipped"] += 1
            summary["errors"] += 1
            return

    refs = data.get("sources") or []
    source_ids, missing, non_verified = resolve_sources(db, refs)

    status_target = data.get("status_target", "draft")
    final_status, reasons = should_publish(
        status_target=status_target,
        missing_sources=missing,
        non_verified_publishers=non_verified,
        unknown_tools=unknown,
    )
    for r in reasons:
        logger.warning("[%s] %s", name, r)
    if final_status == "skip":
        summary["skipped"] += 1
        return

    new_payload = _payload_from_fixture(data)
    new_hash = content_hash(new_payload)
    existing = _fetch_existing(db, name)

    if existing is None:
        if dry_run:
            logger.info("[%s] dry-run create status=%s", name, final_status)
        else:
            _insert_skill(db, data=data, final_status=final_status, version=1)
            inserted = _fetch_existing(db, name)
            if inserted is not None:
                _link_sources(db, inserted["id"], source_ids)
        summary["created"] += 1
        if final_status == "published":
            summary["published"] += 1
        else:
            summary["draft"] += 1
        if is_critical:
            summary["golden_examples"] += len(golden)
        logger.info("[%s] action=created status=%s version=1", name, final_status)
        return

    existing_hash = content_hash(_payload_from_db(existing))
    existing_status = existing["status"]

    # ne jamais rétrograder published → draft
    if existing_status == "published" and final_status == "draft":
        final_status = "published"

    # protéger une skill published modifiée manuellement
    manual_edit = (
        existing_hash != new_hash and existing_status == "published" and not force
    )
    if manual_edit:
        logger.warning(
            "[%s] published modifie manuellement — passe (utilise --force).",
            name,
        )
        summary["skipped"] += 1
        return

    if existing_hash == new_hash and existing_status == final_status:
        logger.info(
            "[%s] action=noop status=%s version=%d",
            name,
            final_status,
            existing["version"],
        )
        if final_status == "published":
            summary["published"] += 1
        else:
            summary["draft"] += 1
        if is_critical:
            summary["golden_examples"] += len(golden)
        return

    new_version = (
        existing["version"] + 1 if existing_hash != new_hash else existing["version"]
    )
    if dry_run:
        logger.info(
            "[%s] dry-run update status=%s version=%d",
            name,
            final_status,
            new_version,
        )
    else:
        _update_skill(
            db,
            existing=existing,
            data=data,
            final_status=final_status,
            new_version=new_version,
        )
        _link_sources(db, existing["id"], source_ids)
    summary["updated"] += 1
    if final_status == "published":
        summary["published"] += 1
    else:
        summary["draft"] += 1
    if is_critical:
        summary["golden_examples"] += len(golden)
    logger.info(
        "[%s] action=updated status=%s version=%d", name, final_status, new_version
    )


def run_seed(
    *,
    seeds_dir: Path = DEFAULT_SEEDS_DIR,
    only: list[str] | None = None,
    force: bool = False,
    dry_run: bool = False,
    db: Session | None = None,
) -> dict[str, Any]:
    started = time.monotonic()
    summary: dict[str, int] = {
        "created": 0,
        "updated": 0,
        "skipped": 0,
        "published": 0,
        "draft": 0,
        "golden_examples": 0,
        "errors": 0,
    }
    fixtures = _iter_fixtures(seeds_dir)
    if only:
        only_set = set(only)
        fixtures = [
            (p, c) for (p, c) in fixtures if p.stem in only_set or p.name in only_set
        ]
    available_tools = known_tools()
    logger.info("Seed start: %d fixtures dans %s", len(fixtures), seeds_dir)

    own_session = db is None
    session = db or SessionLocal()
    try:
        for path, is_critical in fixtures:
            try:
                _process_fixture(
                    session,
                    path=path,
                    is_critical=is_critical,
                    force=force,
                    dry_run=dry_run,
                    available_tools=available_tools,
                    summary=summary,
                )
            except Exception as exc:  # noqa: BLE001
                logger.exception("[%s] erreur inattendue : %s", path.name, exc)
                summary["skipped"] += 1
                summary["errors"] += 1
        if own_session and not dry_run:
            session.commit()
    finally:
        if own_session:
            session.close()

    summary["duration_ms"] = int((time.monotonic() - started) * 1000)
    print(json.dumps(summary, sort_keys=True))
    return summary


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="seed_skills")
    parser.add_argument("--force", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--only", action="append", default=[])
    parser.add_argument("--seeds-dir", type=Path, default=DEFAULT_SEEDS_DIR)
    parser.add_argument("--verbose", "-v", action="store_true")
    args = parser.parse_args(argv)

    _setup_logging(verbose=args.verbose)
    summary = run_seed(
        seeds_dir=args.seeds_dir,
        only=args.only or None,
        force=args.force,
        dry_run=args.dry_run,
    )
    return 1 if (summary.get("errors", 0) or summary.get("skipped", 0)) else 0


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
