"""F02 T068 — Audit des logs : grep des motifs interdits.

Lit un fichier de log (par défaut stdin) et signale toute ligne contenant un
mot de passe en clair, un Bearer JWT, ou la valeur d'un cookie session.

Usage : ``python -m app.scripts.audit_logs < /path/to/log``
Exit 0 si rien trouvé, exit 1 sinon.
"""

from __future__ import annotations

import re
import sys

PATTERNS = [
    re.compile(r"password\s*=\s*\S+", re.IGNORECASE),
    re.compile(r"Bearer\s+ey[A-Za-z0-9_\-]+\.", re.IGNORECASE),
    re.compile(r"mefali_at\s*=\s*\S+"),
    re.compile(r"mefali_rt\s*=\s*\S+"),
]


def scan(stream) -> list[str]:
    findings: list[str] = []
    for ln, line in enumerate(stream, start=1):
        for pat in PATTERNS:
            if pat.search(line):
                findings.append(f"L{ln}: {line.rstrip()}")
                break
    return findings


def main() -> int:
    findings = scan(sys.stdin)
    if findings:
        print("Motifs interdits détectés :", file=sys.stderr)
        for f in findings:
            print(f, file=sys.stderr)
        return 1
    print("OK — aucun motif interdit dans les logs.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
