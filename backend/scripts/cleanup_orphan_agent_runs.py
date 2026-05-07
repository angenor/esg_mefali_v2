"""Cleanup one-shot des ``agent_run`` orphelins (post-fix bug 1.1).

Avant le fix tracing (PR fix/agent-tracing-completed-at), une fermeture
client SSE non-gérée laissait certains rows ``agent_run`` avec
``completed_at IS NULL`` indéfiniment. Ce script normalise ces rows en
les marquant ``status='cancelled'`` avec ``completed_at = started_at +
30s`` (durée arbitraire mais bornée par ``LLM_AGENT_TIMEOUT_S``).

Usage::

    cd backend && source .venv/bin/activate
    python scripts/cleanup_orphan_agent_runs.py            # dry-run par défaut
    python scripts/cleanup_orphan_agent_runs.py --apply    # exécute le UPDATE
    python scripts/cleanup_orphan_agent_runs.py --apply --older-than-minutes 60
        # ne touche que les runs orphelins de plus de 60 min (par défaut 30)

Pas placé dans une migration Alembic — l'opération est ponctuelle, doit
être exécutée manuellement par un opérateur après validation, et ne fait
pas partie du schéma. La table reste auditée comme avant
(``agent_run`` n'est PAS strictement append-only — P3 ne s'applique
qu'à ``audit_log``).
"""

from __future__ import annotations

import argparse
import logging
import sys

from sqlalchemy import text

from app.db import get_engine_migrator

logger = logging.getLogger("cleanup_orphan_agent_runs")
logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Exécute le UPDATE (sans cette flag, le script est en dry-run).",
    )
    parser.add_argument(
        "--older-than-minutes",
        type=int,
        default=30,
        help=(
            "Ne traite que les runs dont started_at est plus ancien que "
            "N minutes (défaut: 30)."
        ),
    )
    parser.add_argument(
        "--default-latency-seconds",
        type=int,
        default=30,
        help=(
            "Latence assumée pour reconstituer completed_at "
            "(=started_at + N s ; défaut: 30)."
        ),
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()

    engine = get_engine_migrator()
    older_than_clause = (
        f"started_at < NOW() - INTERVAL '{args.older_than_minutes} minutes'"
    )

    # 1. Compter les rows concernés.
    with engine.connect() as conn:
        count_row = conn.execute(
            text(
                "SELECT COUNT(*) FROM agent_run "
                "WHERE completed_at IS NULL "
                f"AND {older_than_clause}"
            )
        ).fetchone()
    total = int(count_row[0]) if count_row else 0
    logger.info(
        "Trouvé %d agent_run orphelins (started_at > %d min, completed_at NULL)",
        total,
        args.older_than_minutes,
    )

    if total == 0:
        logger.info("Rien à faire.")
        return 0

    if not args.apply:
        logger.info("--apply absent → DRY-RUN. Aucune mutation effectuée.")
        # Affiche un échantillon
        with engine.connect() as conn:
            sample = (
                conn.execute(
                    text(
                        "SELECT id, started_at, status FROM agent_run "
                        "WHERE completed_at IS NULL "
                        f"AND {older_than_clause} "
                        "ORDER BY started_at DESC LIMIT 5"
                    )
                )
                .fetchall()
            )
        logger.info("Échantillon (5 plus récents) :")
        for row in sample:
            logger.info("  - %s  started_at=%s  status=%s", row[0], row[1], row[2])
        return 0

    # 2. UPDATE
    update_sql = text(
        "UPDATE agent_run SET "
        " completed_at = started_at + (:lat * INTERVAL '1 second'), "
        " status = 'cancelled', "
        " error_summary = COALESCE(error_summary, "
        "  'orphan run normalized by cleanup_orphan_agent_runs.py') "
        "WHERE completed_at IS NULL "
        f"AND {older_than_clause}"
    )
    with engine.begin() as conn:
        result = conn.execute(update_sql, {"lat": args.default_latency_seconds})
    affected = result.rowcount or 0
    logger.info("UPDATE exécuté → %d rows normalisés (status=cancelled).", affected)
    return 0


if __name__ == "__main__":
    sys.exit(main())
