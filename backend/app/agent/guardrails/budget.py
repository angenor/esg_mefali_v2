"""F58 — Budget tokens guardrail (FR-012, FR-013, FR-014, FR-015).

Sous-quotas distincts par flow :
- ``conversation`` (défaut 30 000 tokens / jour) ;
- ``ocr_analysis`` (défaut 20 000 tokens / jour) ;
- total cohérent ≤ ``daily_token_quota`` (CHECK DB ``ck_account_quota_sum``).

Les compteurs sont calculés à la volée via agrégation de ``agent_run_step``
filtrée par ``account_id``, ``flow``, ``started_at >= aujourd'hui UTC``.
Cache 60 s in-memory pour éviter une requête par tour.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from time import monotonic
from typing import Final, Literal
from uuid import UUID

from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

Flow = Literal["conversation", "ocr_analysis"]

MAX_COMPLETION_TOKENS_PER_TURN: Final[int] = 8000
_CACHE_TTL_S: Final[float] = 60.0


@dataclass(frozen=True)
class BudgetResult:
    """Résultat d'un appel à :func:`check_budget`. Immutable."""

    allowed: bool
    flow: Flow
    requested_tokens: int
    remaining_conversation_tokens: int
    remaining_ocr_analysis_tokens: int
    reason: str | None  # FR-014 — message poli FR si refusé


# ---------------------------------------------------------------------------
# Cache simple TTL 60s : (account_id, day) → (consumed_conv, consumed_ocr)
# ---------------------------------------------------------------------------

_CACHE: dict[tuple[UUID, date], tuple[float, int, int]] = {}


def _today_utc_start() -> datetime:
    """Renvoie le début du jour UTC (réinitialisation des compteurs)."""
    today = datetime.now(UTC).date()
    return datetime.combine(today, time.min, tzinfo=UTC)


def _read_consumed(db: Session, account_id: UUID) -> tuple[int, int]:
    """Lit ``(consumed_conversation, consumed_ocr_analysis)`` pour aujourd'hui.

    Best-effort : retourne ``(0, 0)`` si requête échoue (jamais bloquant).
    Filtre sur ``started_at >= today UTC`` (réinit minuit UTC, cf. spec).
    """
    today = datetime.now(UTC).date()
    cached = _CACHE.get((account_id, today))
    if cached is not None:
        ts, conv, ocr = cached
        if (monotonic() - ts) < _CACHE_TTL_S:
            return conv, ocr
    consumed_conv = 0
    consumed_ocr = 0
    try:
        rows = (
            db.execute(
                text(
                    """
                    SELECT flow,
                           COALESCE(SUM(COALESCE(tokens_in,0) + COALESCE(tokens_out,0)), 0) AS tot
                    FROM agent_run_step
                    WHERE account_id = :aid AND started_at >= :since
                    GROUP BY flow
                    """
                ),
                {"aid": account_id, "since": _today_utc_start()},
            )
            .mappings()
            .all()
        )
        for r in rows:
            flow = str(r.get("flow") or "conversation")
            tot = int(r.get("tot") or 0)
            if flow == "ocr_analysis":
                consumed_ocr += tot
            else:
                consumed_conv += tot
    except Exception:  # noqa: BLE001
        logger.debug("read_consumed failed (returning 0,0)", exc_info=True)
    _CACHE[(account_id, today)] = (monotonic(), consumed_conv, consumed_ocr)
    return consumed_conv, consumed_ocr


def _read_quotas(db: Session, account_id: UUID) -> tuple[int, int, int]:
    """Lit ``(daily_total, daily_conv, daily_ocr)`` depuis ``account``.

    Best-effort : fallback sur les valeurs par défaut (50K/30K/20K) si la
    requête échoue.
    """
    try:
        row = (
            db.execute(
                text(
                    "SELECT daily_token_quota AS tot, "
                    "daily_conversation_quota AS conv, "
                    "daily_ocr_analysis_quota AS ocr "
                    "FROM account WHERE id = :aid"
                ),
                {"aid": account_id},
            )
            .mappings()
            .first()
        )
        if row:
            return (
                int(row.get("tot") or 50000),
                int(row.get("conv") or 30000),
                int(row.get("ocr") or 20000),
            )
    except Exception:  # noqa: BLE001
        logger.debug("read_quotas failed (using defaults)", exc_info=True)
    return 50000, 30000, 20000


def check_budget(
    db: Session,
    *,
    account_id: UUID,
    requested_tokens: int,
    flow: Flow = "conversation",
) -> BudgetResult:
    """Vérifie si une requête peut consommer ``requested_tokens``.

    Règles (FR-013) :
    - cap absolu par tour : ``requested_tokens <= 8000``.
    - sous-quota du flux concerné non dépassé.

    Returns:
        :class:`BudgetResult` avec ``allowed`` + raison FR si refusée.
    """
    if requested_tokens > MAX_COMPLETION_TOKENS_PER_TURN:
        return BudgetResult(
            allowed=False,
            flow=flow,
            requested_tokens=requested_tokens,
            remaining_conversation_tokens=0,
            remaining_ocr_analysis_tokens=0,
            reason=(
                f"Limite de {MAX_COMPLETION_TOKENS_PER_TURN} tokens par tour "
                "dépassée — requête trop volumineuse."
            ),
        )

    _, daily_conv, daily_ocr = _read_quotas(db, account_id)
    consumed_conv, consumed_ocr = _read_consumed(db, account_id)
    remaining_conv = max(0, daily_conv - consumed_conv)
    remaining_ocr = max(0, daily_ocr - consumed_ocr)

    if flow == "conversation":
        if remaining_conv < requested_tokens:
            return BudgetResult(
                allowed=False,
                flow=flow,
                requested_tokens=requested_tokens,
                remaining_conversation_tokens=remaining_conv,
                remaining_ocr_analysis_tokens=remaining_ocr,
                reason=(
                    "Quota conversation quotidien atteint — merci de revenir "
                    "demain ou de contacter votre administrateur pour un "
                    "ajustement de quota."
                ),
            )
    else:  # ocr_analysis
        if remaining_ocr < requested_tokens:
            return BudgetResult(
                allowed=False,
                flow=flow,
                requested_tokens=requested_tokens,
                remaining_conversation_tokens=remaining_conv,
                remaining_ocr_analysis_tokens=remaining_ocr,
                reason=(
                    "Quota analyse / OCR quotidien atteint — merci de revenir "
                    "demain ou de contacter votre administrateur."
                ),
            )

    return BudgetResult(
        allowed=True,
        flow=flow,
        requested_tokens=requested_tokens,
        remaining_conversation_tokens=remaining_conv,
        remaining_ocr_analysis_tokens=remaining_ocr,
        reason=None,
    )


def cap_completion_tokens(
    requested: int,
    *,
    max_per_turn: int = MAX_COMPLETION_TOKENS_PER_TURN,
) -> int:
    """Renvoie ``min(requested, max_per_turn)``.

    Utilisé pour le paramètre ``max_tokens`` de l'appel LLM (FR-015).
    """
    return min(requested, max_per_turn)


def _reset_cache() -> None:
    """Réservé aux tests."""
    _CACHE.clear()


__all__ = [
    "MAX_COMPLETION_TOKENS_PER_TURN",
    "BudgetResult",
    "Flow",
    "_reset_cache",
    "cap_completion_tokens",
    "check_budget",
]
