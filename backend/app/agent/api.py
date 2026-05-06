"""F53 / T064 — Endpoint ``GET /health/agent``.

Conforme à ``contracts/healthcheck-agent.openapi.yaml``.
"""

from __future__ import annotations

import logging
from typing import Any

import httpx
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from app.config import get_settings

logger = logging.getLogger(__name__)

router = APIRouter(tags=["health"])


async def _ping_llm(*, base_url: str, timeout_s: float) -> bool:
    """Tente un HEAD/GET court vers ``base_url/models`` ; True si 2xx/3xx."""
    url = base_url.rstrip("/") + "/models"
    try:
        async with httpx.AsyncClient(timeout=timeout_s) as client:
            r = await client.get(url)
            return r.status_code < 500
    except Exception:  # noqa: BLE001
        return False


@router.get("/health/agent")
async def get_agent_health(request: Request) -> Any:
    """Healthcheck de l'agent ESG Mefali.

    Retourne 200 si tous les checks sont verts, 503 sinon.
    """
    settings = get_settings()
    mode = settings.LLM_AGENT_MODE

    # Le compile + checkpointer setup sont stockés sur app.state au boot
    # par main.py (lifespan). En mode raw on les considère non requis.
    app_state = getattr(request.app, "state", None)
    langgraph_compiled = bool(getattr(app_state, "agent_graph", None))
    postgres_checkpointer = bool(getattr(app_state, "agent_checkpointer", None))
    boot_duration_ms = getattr(app_state, "agent_boot_duration_ms", None)

    llm_reachable = await _ping_llm(
        base_url=settings.LLM_BASE_URL,
        timeout_s=settings.LLM_HEALTH_TIMEOUT_S,
    )

    if mode == "raw":
        ok = llm_reachable
    else:
        ok = langgraph_compiled and postgres_checkpointer and llm_reachable

    payload: dict[str, Any] = {
        "ok": ok,
        "langgraph_compiled": langgraph_compiled,
        "postgres_checkpointer": postgres_checkpointer,
        "llm_reachable": llm_reachable,
        "mode": mode,
    }
    if boot_duration_ms is not None:
        payload["boot_duration_ms"] = int(boot_duration_ms)
    if not ok:
        payload["error"] = _summarize_error(payload)

    status_code = 200 if ok else 503
    return JSONResponse(status_code=status_code, content=payload)


def _summarize_error(payload: dict[str, Any]) -> str:
    bits: list[str] = []
    if not payload.get("langgraph_compiled"):
        bits.append("langgraph not compiled")
    if not payload.get("postgres_checkpointer"):
        bits.append("postgres checkpointer down")
    if not payload.get("llm_reachable"):
        bits.append("LLM unreachable")
    return "; ".join(bits) if bits else "degraded"


__all__ = ["router"]
