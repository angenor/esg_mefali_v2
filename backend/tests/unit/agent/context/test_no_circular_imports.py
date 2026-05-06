"""F54 / T073 — Garde-fou NFR-004 : service pur.

Vérifie via AST que ``app.agent.context.*`` et ``app.agent.prompt_builder``
n'importent **PAS** ``app.chat.api`` ni ``app.agent.runner``.

Ces dépendances créeraient des imports circulaires et trahiraient le
contrat de service pur (NFR-004).
"""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

_PROJECT_ROOT = Path(__file__).parents[5]
_BACKEND_APP = _PROJECT_ROOT / "backend" / "app"

#: Modules concernés par la règle "service pur".
_PURE_MODULES = [
    _BACKEND_APP / "agent" / "context",
    _BACKEND_APP / "agent" / "prompt_builder.py",
    _BACKEND_APP / "agent" / "prompts",
]

#: Imports interdits (forme `app.<...>`).
_FORBIDDEN_IMPORTS = {
    "app.chat.api",
    "app.agent.runner",
}


def _iter_python_files(p: Path):
    if p.is_file() and p.suffix == ".py":
        yield p
    elif p.is_dir():
        for f in p.rglob("*.py"):
            if "__pycache__" in f.parts:
                continue
            yield f


def _imports_of(file_path: Path) -> set[str]:
    """Retourne l'ensemble des modules importés par ``file_path``."""
    tree = ast.parse(file_path.read_text(encoding="utf-8"), filename=str(file_path))
    imports: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imports.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.add(node.module)
                # Ajouter aussi tous les imports de nom comme app.X.Y.
                for alias in node.names:
                    imports.add(f"{node.module}.{alias.name}")
    return imports


@pytest.mark.unit
class TestNoCircularImports:
    def test_app_agent_context_does_not_import_runner_or_chat_api(self) -> None:
        violations: list[tuple[str, str]] = []
        for module_path in _PURE_MODULES:
            for f in _iter_python_files(module_path):
                imports = _imports_of(f)
                for forbidden in _FORBIDDEN_IMPORTS:
                    if any(imp.startswith(forbidden) for imp in imports):
                        violations.append((str(f), forbidden))
        assert not violations, (
            "Service pur (NFR-004) violé. Imports interdits trouvés :\n"
            + "\n".join(f"  - {v[0]} importe {v[1]}" for v in violations)
        )

    def test_target_modules_exist(self) -> None:
        """Sanity check : les modules à tester existent vraiment."""
        for p in _PURE_MODULES:
            assert p.exists(), f"Module manquant : {p}"
