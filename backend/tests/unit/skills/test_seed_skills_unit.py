"""F21 — Tests unitaires du script seed_skills (logique pure, sans DB)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from scripts import seed_skills as sk


def _write_fixture(seeds_dir: Path, sub: str, name: str, **overrides) -> Path:
    target = seeds_dir / sub
    target.mkdir(parents=True, exist_ok=True)
    payload = {
        "name": name,
        "domain": "diagnostic_esg",
        "language_default": "fr",
        "status_target": "draft",
        "sources": [],
        "activation_rules": {"any_of": [{"page": "/diag"}]},
        "tool_whitelist": ["ask_qcu"],
        "prompt_expert": "Expert ESG.",
        "procedure": "1. extraire 2. completer 3. synthetiser",
        "golden_examples": [],
    }
    payload.update(overrides)
    path = target / f"{name}.yaml"
    path.write_text(yaml.safe_dump(payload, sort_keys=False), encoding="utf-8")
    return path


def test_iter_fixtures_orders_critical_first(tmp_path: Path) -> None:
    _write_fixture(tmp_path, "shells", "shell_a")
    _write_fixture(tmp_path, "critical", "crit_a")
    _write_fixture(tmp_path, "shells", "shell_b")

    out = sk._iter_fixtures(tmp_path)
    names = [(p.name, c) for p, c in out]
    assert names[0] == ("crit_a.yaml", True)
    assert all(c is False for _, c in names[1:])
    assert {"shell_a.yaml", "shell_b.yaml"} == {n for n, _ in names[1:]}


def test_iter_fixtures_empty_dir_returns_empty(tmp_path: Path) -> None:
    assert sk._iter_fixtures(tmp_path) == []


def test_payload_from_fixture_canonical_keys() -> None:
    data = {
        "name": "x",
        "prompt_expert": "p",
        "activation_rules": {"a": 1},
        "tool_whitelist": ["t"],
        "procedure": "proc",
        "extra_key": "ignored",
    }
    p = sk._payload_from_fixture(data)
    assert set(p.keys()) == {
        "prompt_expert",
        "activation_rules",
        "tool_whitelist",
        "procedure",
    }
    assert p["activation_rules"] == {"a": 1}
    assert "extra_key" not in p


def test_payload_from_db_handles_missing_fields() -> None:
    p = sk._payload_from_db({})
    assert p == {
        "prompt_expert": "",
        "activation_rules": {},
        "tool_whitelist": [],
        "procedure": "",
    }


def test_main_help_exits_zero() -> None:
    with pytest.raises(SystemExit) as exc:
        sk.main(["--help"])
    assert exc.value.code == 0


def test_main_dry_run_with_empty_seeds(monkeypatch, tmp_path: Path) -> None:
    """Le mode dry-run sur dossier vide termine avec rc=0."""

    class _Sess:
        def execute(self, *_a, **_k):
            class _R:
                def first(self):
                    return None

                def all(self):
                    return []

            return _R()

        def commit(self):
            pass

        def close(self):
            pass

    monkeypatch.setattr(sk, "SessionLocal", lambda: _Sess())
    rc = sk.main(["--dry-run", "--seeds-dir", str(tmp_path)])
    assert rc == 0


def test_run_seed_uses_provided_session(monkeypatch, tmp_path: Path) -> None:
    """Si on passe un ``db`` explicite, ``SessionLocal`` n'est pas appele."""

    class _SessNoCalls:
        def execute(self, *_a, **_k):
            class _R:
                def first(self):
                    return None

                def all(self):
                    return []

            return _R()

        def commit(self):
            raise AssertionError("commit ne doit pas etre appele en dry-run")

        def close(self):
            raise AssertionError("close ne doit pas etre appele si db=...")

    sentinel = {"called": False}

    def _fail():
        sentinel["called"] = True
        raise AssertionError("SessionLocal ne doit pas etre invoque")

    monkeypatch.setattr(sk, "SessionLocal", _fail)
    sk.run_seed(seeds_dir=tmp_path, dry_run=True, db=_SessNoCalls())
    assert sentinel["called"] is False


def test_process_fixture_skips_invalid_shape(tmp_path: Path) -> None:
    """Une fixture sans `prompt_expert` est skippee + comptee en errors."""
    path = _write_fixture(tmp_path, "critical", "bad", prompt_expert="")
    summary = {
        "created": 0, "updated": 0, "skipped": 0,
        "published": 0, "draft": 0, "golden_examples": 0, "errors": 0,
    }

    class _Sess:
        def execute(self, *_a, **_k):
            class _R:
                def first(self):
                    return None
            return _R()

    sk._process_fixture(
        _Sess(),  # type: ignore[arg-type]
        path=path,
        is_critical=True,
        force=False,
        dry_run=True,
        available_tools={"ask_qcu"},
        summary=summary,
    )
    assert summary["skipped"] == 1
    assert summary["errors"] == 1


class _StubMapping:
    def __init__(self, mapping: dict):
        self._mapping = mapping


class _StubResult:
    def __init__(self, row=None):  # noqa: ANN001
        self._row = row

    def first(self):
        return self._row


class _StubSession:
    """Session stub minimaliste pour tester les chemins sans I/O reelle."""

    def __init__(self, fetch_existing_row=None):  # noqa: ANN001
        self._fetch = (
            _StubMapping(fetch_existing_row) if fetch_existing_row else None
        )
        self.executed = []
        self.committed = False

    def execute(self, stmt, params=None):  # noqa: ANN001
        self.executed.append(str(stmt))
        return _StubResult(self._fetch)

    def commit(self):
        self.committed = True


def _summary() -> dict:
    return {
        "created": 0, "updated": 0, "skipped": 0,
        "published": 0, "draft": 0, "golden_examples": 0, "errors": 0,
    }


def test_process_fixture_create_dry_run(tmp_path: Path) -> None:
    """Dry-run sur skill nouvelle : created++ sans appel DB ecrit."""
    path = _write_fixture(
        tmp_path, "shells", "skill_new",
        tool_whitelist=["ask_qcu"],
    )
    summary = _summary()
    sk._process_fixture(
        _StubSession(fetch_existing_row=None),  # type: ignore[arg-type]
        path=path,
        is_critical=False,
        force=False,
        dry_run=True,
        available_tools={"ask_qcu"},
        summary=summary,
    )
    assert summary["created"] == 1
    assert summary["draft"] == 1


def test_process_fixture_noop_when_unchanged(tmp_path: Path) -> None:
    """Hash identique + statut identique → noop."""
    path = _write_fixture(
        tmp_path, "shells", "skill_same",
        tool_whitelist=["ask_qcu"],
    )
    # Calculer le hash attendu pour matcher exactly.
    from app.skills.seed_helpers import content_hash, load_skill_yaml

    data = load_skill_yaml(path)
    h = content_hash({
        "prompt_expert": data["prompt_expert"],
        "activation_rules": data["activation_rules"],
        "tool_whitelist": data["tool_whitelist"],
        "procedure": data["procedure"],
    })
    existing_row = {
        "id": "00000000-0000-0000-0000-000000000001",
        "name": "skill_same",
        "version": 1,
        "status": "draft",
        "prompt_expert": data["prompt_expert"],
        "activation_rules": data["activation_rules"],
        "tool_whitelist": data["tool_whitelist"],
        "procedure": data["procedure"],
        "valid_from": None,
    }
    # sanity: on construit le row tel que content_hash(_payload_from_db) == h
    assert content_hash(sk._payload_from_db(existing_row)) == h

    summary = _summary()
    sk._process_fixture(
        _StubSession(fetch_existing_row=existing_row),  # type: ignore[arg-type]
        path=path,
        is_critical=False,
        force=False,
        dry_run=True,
        available_tools={"ask_qcu"},
        summary=summary,
    )
    # noop → ni created ni updated, mais comptage statut.
    assert summary["created"] == 0
    assert summary["updated"] == 0
    assert summary["draft"] == 1


def test_process_fixture_dry_run_update_bumps_version(tmp_path: Path) -> None:
    """Hash different en dry-run → updated++ et version logguee = N+1."""
    path = _write_fixture(
        tmp_path, "shells", "skill_change",
        tool_whitelist=["ask_qcu"],
    )
    existing_row = {
        "id": "00000000-0000-0000-0000-000000000002",
        "name": "skill_change",
        "version": 3,
        "status": "draft",
        "prompt_expert": "ANCIEN PROMPT",
        "activation_rules": {},
        "tool_whitelist": ["ask_qcu"],
        "procedure": "ancien",
        "valid_from": None,
    }
    summary = _summary()
    sk._process_fixture(
        _StubSession(fetch_existing_row=existing_row),  # type: ignore[arg-type]
        path=path,
        is_critical=False,
        force=False,
        dry_run=True,
        available_tools={"ask_qcu"},
        summary=summary,
    )
    assert summary["updated"] == 1


def test_process_fixture_protects_published_manual_edit(tmp_path: Path) -> None:
    """Skill published avec hash different sans --force → skipped."""
    path = _write_fixture(
        tmp_path, "shells", "skill_locked",
        tool_whitelist=["ask_qcu"],
    )
    existing_row = {
        "id": "00000000-0000-0000-0000-000000000003",
        "name": "skill_locked",
        "version": 5,
        "status": "published",
        "prompt_expert": "AUTRE PROMPT",
        "activation_rules": {},
        "tool_whitelist": ["ask_qcu"],
        "procedure": "autre",
        "valid_from": None,
    }
    summary = _summary()
    sk._process_fixture(
        _StubSession(fetch_existing_row=existing_row),  # type: ignore[arg-type]
        path=path,
        is_critical=False,
        force=False,
        dry_run=True,
        available_tools={"ask_qcu"},
        summary=summary,
    )
    assert summary["skipped"] == 1


def test_process_fixture_skips_unknown_tool(tmp_path: Path) -> None:
    """Tool absent du registry → skip sans exception."""
    path = _write_fixture(
        tmp_path, "critical", "ok", tool_whitelist=["bad_tool"],
        procedure=("1. " + "x" * 250),
        golden_examples=[
            {
                "input_message": "m",
                "page_context": "/diag",
                "intent": "analyse",
                "expected_tool": "bad_tool",
                "expected_payload_partial": {},
            }
            for _ in range(5)
        ],
    )
    summary = {
        "created": 0, "updated": 0, "skipped": 0,
        "published": 0, "draft": 0, "golden_examples": 0, "errors": 0,
    }

    class _Sess:
        def execute(self, *_a, **_k):
            class _R:
                def first(self):
                    return None
            return _R()

    sk._process_fixture(
        _Sess(),  # type: ignore[arg-type]
        path=path,
        is_critical=True,
        force=False,
        dry_run=True,
        available_tools={"ask_qcu"},
        summary=summary,
    )
    assert summary["skipped"] == 1
