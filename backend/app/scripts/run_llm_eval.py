"""F35 — CLI : exécute le golden set localement via un stub LLM.

Usage : ``python -m app.scripts.run_llm_eval [--filter=tag1,tag2] [--output=json|markdown]``
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from app.api.routes.admin_llm_eval import _stub_llm_callable
from app.eval.eval_runner import run_eval
from app.eval.golden_loader import load_cases
from app.eval.report import to_json, to_markdown


def _default_path() -> Path:
    return Path(__file__).resolve().parents[2] / "tests" / "llm_eval" / "golden_seed.json"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="F35 — Golden set eval runner")
    parser.add_argument("--path", type=Path, default=_default_path())
    parser.add_argument("--filter", type=str, default=None)
    parser.add_argument("--output", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args(argv)

    filter_tags = [t.strip() for t in args.filter.split(",")] if args.filter else None
    cases = load_cases(args.path, filter_tags=filter_tags)
    report = run_eval(cases, llm_callable=_stub_llm_callable)

    if args.output == "json":
        sys.stdout.write(to_json(report) + "\n")
    else:
        sys.stdout.write(to_markdown(report))
    return 0


if __name__ == "__main__":
    sys.exit(main())
