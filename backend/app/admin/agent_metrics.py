"""F56 / T048 (US9) — Endpoint admin métriques sourcing.

``GET /admin/agent/metrics/sourcing?period=7d|30d|all`` retourne les KPIs
de compliance de l'agent : compliance_rate, unsourced_rate, retry_rate,
fallback_rate, top_sources, top_unsourced_topics.

Référence : ``contracts/admin-metrics.md``.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
from typing import Any, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.admin.deps import require_admin
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter()


# ---------------------------------------------------------------------------
# Pydantic response schema
# ---------------------------------------------------------------------------


class TopSource(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_id: UUID
    title: str | None = None
    publisher: str | None = None
    citation_count: int = Field(ge=0)


class TopUnsourcedTopic(BaseModel):
    model_config = ConfigDict(extra="forbid")

    claim: str
    count: int = Field(ge=0)
    first_seen: datetime


class SourcingMetricsResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    period: Literal["7d", "30d", "all"]
    computed_at: datetime
    compliance_rate: float = Field(ge=0.0, le=1.0)
    unsourced_rate: float = Field(ge=0.0, le=1.0)
    retry_rate: float = Field(ge=0.0, le=1.0)
    fallback_rate: float = Field(ge=0.0, le=1.0)
    total_runs: int = Field(ge=0)
    runs_with_citation: int = Field(ge=0)
    runs_with_unsourced: int = Field(ge=0)
    runs_with_retry: int = Field(ge=0)
    runs_with_fallback: int = Field(ge=0)
    top_sources: list[TopSource] = Field(default_factory=list, max_length=20)
    top_unsourced_topics: list[TopUnsourcedTopic] = Field(
        default_factory=list, max_length=20
    )


# ---------------------------------------------------------------------------
# Cache léger en mémoire (5 min) — fallback si Redis non dispo en test
# ---------------------------------------------------------------------------

_CACHE: dict[str, tuple[datetime, SourcingMetricsResponse]] = {}
_TTL_SECONDS = 300


def _period_to_since(period: str) -> datetime | None:
    """Retourne le ``since`` datetime pour ``period``, ou ``None`` pour ``all``."""
    now = datetime.now(UTC)
    if period == "7d":
        return now - timedelta(days=7)
    if period == "30d":
        return now - timedelta(days=30)
    return None


def _ratio(num: int, den: int) -> float:
    if den <= 0:
        return 0.0
    return round(num / den, 4)


def _compute_metrics(
    db: Session, period: Literal["7d", "30d", "all"]
) -> SourcingMetricsResponse:
    """Compute live metrics depuis ``agent_run`` + ``chat_message`` + ``unsourced_flag``.

    Best-effort en cas de tables manquantes (retourne 0).
    """
    since = _period_to_since(period)
    where_clause = "WHERE created_at >= :since" if since else ""
    params: dict[str, Any] = {"since": since} if since else {}

    total_runs = 0
    runs_with_citation = 0
    runs_with_retry = 0
    runs_with_fallback = 0
    runs_with_unsourced = 0
    top_sources: list[TopSource] = []
    top_unsourced_topics: list[TopUnsourcedTopic] = []

    # 1. Total runs + retry + fallback + with_citation depuis agent_run
    try:
        row = (
            db.execute(
                text(
                    f"""
                    SELECT
                      count(*) AS total,
                      sum(CASE WHEN sourcing_status IN ('retried_ok', 'failed')
                          THEN 1 ELSE 0 END) AS retried,
                      sum(CASE WHEN sourcing_status = 'failed'
                          THEN 1 ELSE 0 END) AS fallback,
                      sum(CASE WHEN sourcing_status IN ('ok', 'retried_ok')
                          THEN 1 ELSE 0 END) AS ok_or_retried
                    FROM agent_run
                    {where_clause}
                    """
                ),
                params,
            )
            .mappings()
            .first()
        )
        if row:
            total_runs = int(row.get("total") or 0)
            runs_with_retry = int(row.get("retried") or 0)
            runs_with_fallback = int(row.get("fallback") or 0)
            runs_with_citation = int(row.get("ok_or_retried") or 0)
    except Exception:  # noqa: BLE001 - best effort
        pass

    # 2. runs_with_unsourced from unsourced_flag
    try:
        flag_where = "WHERE created_at >= :since" if since else ""
        unsourced_count_row = (
            db.execute(
                text(
                    f"""
                    SELECT count(DISTINCT agent_run_id) AS n
                    FROM unsourced_flag
                    {flag_where}
                      {'AND' if since else 'WHERE'} agent_run_id IS NOT NULL
                    """
                ),
                params,
            )
            .mappings()
            .first()
        )
        if unsourced_count_row:
            runs_with_unsourced = int(unsourced_count_row.get("n") or 0)
    except Exception:  # noqa: BLE001
        pass

    # 3. Top sources from chat_message.sources JSONB
    try:
        msg_where = "WHERE created_at >= :since" if since else ""
        rows = (
            db.execute(
                text(
                    f"""
                    SELECT (s->>'source_id')::uuid AS source_id,
                           MIN(s->>'title') AS title,
                           MIN(s->>'publisher') AS publisher,
                           count(*) AS citation_count
                    FROM chat_message m,
                         jsonb_array_elements(COALESCE(m.sources, '[]'::jsonb)) AS s
                    {msg_where}
                    GROUP BY (s->>'source_id')::uuid
                    ORDER BY citation_count DESC
                    LIMIT 20
                    """
                ),
                params,
            )
            .mappings()
            .all()
        )
        for r in rows:
            sid = r.get("source_id")
            if sid is None:
                continue
            top_sources.append(
                TopSource(
                    source_id=sid,
                    title=r.get("title"),
                    publisher=r.get("publisher"),
                    citation_count=int(r.get("citation_count") or 0),
                )
            )
    except Exception:  # noqa: BLE001
        pass

    # 4. Top unsourced topics
    try:
        flag_where = "WHERE created_at >= :since" if since else ""
        suffix = "AND" if since else "WHERE"
        rows = (
            db.execute(
                text(
                    f"""
                    SELECT lower(claim) AS claim,
                           count(*) AS count,
                           min(created_at) AS first_seen
                    FROM unsourced_flag
                    {flag_where} {suffix} resolved_at IS NULL
                    GROUP BY lower(claim)
                    ORDER BY count DESC
                    LIMIT 20
                    """
                ),
                params,
            )
            .mappings()
            .all()
        )
        for r in rows:
            top_unsourced_topics.append(
                TopUnsourcedTopic(
                    claim=str(r.get("claim") or ""),
                    count=int(r.get("count") or 0),
                    first_seen=r.get("first_seen") or datetime.now(UTC),
                )
            )
    except Exception:  # noqa: BLE001
        pass

    return SourcingMetricsResponse(
        period=period,
        computed_at=datetime.now(UTC),
        compliance_rate=_ratio(runs_with_citation, total_runs),
        unsourced_rate=_ratio(runs_with_unsourced, total_runs),
        retry_rate=_ratio(runs_with_retry, total_runs),
        fallback_rate=_ratio(runs_with_fallback, total_runs),
        total_runs=total_runs,
        runs_with_citation=runs_with_citation,
        runs_with_unsourced=runs_with_unsourced,
        runs_with_retry=runs_with_retry,
        runs_with_fallback=runs_with_fallback,
        top_sources=top_sources,
        top_unsourced_topics=top_unsourced_topics,
    )


@router.get(
    "/sourcing",
    response_model=SourcingMetricsResponse,
    summary="F56 — Sourcing compliance metrics",
)
async def get_sourcing_metrics(
    period: Literal["7d", "30d", "all"] = Query(default="7d"),
    db: Session = Depends(get_db),
    admin: AccountUser = Depends(require_admin),  # noqa: ARG001
) -> SourcingMetricsResponse:
    """Retourne les KPIs de compliance sourcing pour ``period``.

    Cache léger en mémoire 5 min par ``period``.
    """
    now = datetime.now(UTC)
    cached = _CACHE.get(period)
    if cached:
        cached_at, value = cached
        if (now - cached_at).total_seconds() < _TTL_SECONDS:
            return value
    metrics = _compute_metrics(db, period)
    _CACHE[period] = (now, metrics)
    return metrics


def reset_metrics_cache() -> None:
    """Réservé aux tests."""
    _CACHE.clear()


__all__ = [
    "SourcingMetricsResponse",
    "TopSource",
    "TopUnsourcedTopic",
    "get_sourcing_metrics",
    "reset_metrics_cache",
    "router",
]
