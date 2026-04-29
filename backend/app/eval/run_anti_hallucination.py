"""F03 US3 — Runner CLI d'eval anti-hallucination.

Usage :
    python -m app.eval.run_anti_hallucination tests/eval/llm_anti_hallucination_set.json

Le set est une liste d'objets ``{"name": str, "expected_accept": bool, "message": dict}``
où ``message`` est un message OpenAI-format (``content`` + ``tool_calls``).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

from app.db import SessionLocal
from app.services.llm_validation import validate_llm_output


def run(eval_set_path: Path) -> int:
    raw = json.loads(eval_set_path.read_text(encoding="utf-8"))
    db = SessionLocal()
    failures: list[dict] = []
    try:
        for case in raw:
            decision = validate_llm_output(db, case["message"])
            ok = decision.accepted == case["expected_accept"]
            if not ok:
                failures.append({"name": case["name"], "decision": decision.__dict__})
    finally:
        db.close()
    total = len(raw)
    passed = total - len(failures)
    print(f"Eval anti-hallucination : {passed}/{total} OK")
    for f in failures:
        print(f"  FAIL {f['name']}: {f['decision']}")
    return 0 if not failures else 1


def main() -> int:
    if len(sys.argv) < 2:
        print("usage: run_anti_hallucination <set.json>", file=sys.stderr)
        return 2
    return run(Path(sys.argv[1]))


if __name__ == "__main__":
    sys.exit(main())
