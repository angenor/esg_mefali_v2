"""Tests d'idempotence des migrations Alembic (T024)."""

from __future__ import annotations

import subprocess
from pathlib import Path

from tests.conftest import requires_db

BACKEND_DIR = Path(__file__).resolve().parents[1]


def _alembic(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["alembic", *args],
        cwd=BACKEND_DIR,
        capture_output=True,
        text=True,
        check=False,
    )


@requires_db
def test_migration_upgrade_downgrade_upgrade_is_idempotent():
    """T024 — upgrade head → downgrade base → upgrade head sans erreur."""
    up1 = _alembic("upgrade", "head")
    assert up1.returncode == 0, f"first upgrade failed: {up1.stderr}"

    down = _alembic("downgrade", "base")
    assert down.returncode == 0, f"downgrade failed: {down.stderr}"

    up2 = _alembic("upgrade", "head")
    assert up2.returncode == 0, f"second upgrade failed: {up2.stderr}"
