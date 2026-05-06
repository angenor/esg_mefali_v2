"""F58 / E2E — Pipeline scripts/eval_agent.py + scripts/eval_jailbreak.py mode mock.

Réservé à e2e-runner. Vérifie que les scripts CLI peuvent être exécutés
en sous-processus, produisent un report.json valide et ont exit 0 en mode
mock sur les fixtures smoke.
"""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

_BACKEND_ROOT = Path(__file__).resolve().parents[2]


@pytest.mark.e2e
def test_e2e_eval_agent_mock_smoke(tmp_path: Path) -> None:
    """`python scripts/eval_agent.py --mode mock` exit 0 sur smoke set."""
    report = tmp_path / "report.json"
    cases = _BACKEND_ROOT / "tests" / "golden" / "agent_e2e_smoke.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            str(_BACKEND_ROOT / "scripts" / "eval_agent.py"),
            "--mode",
            "mock",
            "--threshold",
            "0.5",
            "--cases-file",
            str(cases),
            "--report",
            str(report),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"eval_agent failed: {result.stderr}"
    assert report.exists()
    data = json.loads(report.read_text())
    assert data["mode"] == "mock"
    assert data["total"] >= 1
    assert data["pass_rate"] >= 0.5


@pytest.mark.e2e
def test_e2e_jailbreak_smoke_runs(tmp_path: Path) -> None:
    """`python scripts/eval_jailbreak.py --mode mock` exit 0 sur smoke set."""
    report = tmp_path / "jb_report.json"
    cases = _BACKEND_ROOT / "tests" / "golden" / "jailbreak_smoke.jsonl"
    result = subprocess.run(
        [
            sys.executable,
            str(_BACKEND_ROOT / "scripts" / "eval_jailbreak.py"),
            "--mode",
            "mock",
            "--cases-file",
            str(cases),
            "--report",
            str(report),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, f"eval_jailbreak failed: {result.stderr}"
    assert report.exists()
    data = json.loads(report.read_text())
    assert data["mode"] == "mock"
    assert data["total_cases"] >= 1
    # Aucune fuite détectée
    for k, v in data["indicators"].items():
        assert v == 0, f"jailbreak {k} > 0: {v}"
