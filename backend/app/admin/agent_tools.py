"""F58 / US4 — Endpoints admin kill-switch tool agent (FR-007, FR-008, FR-009).

3 endpoints :
- ``POST /admin/agent/tools/{tool_name}/disable`` ``{reason: str}``
- ``POST /admin/agent/tools/{tool_name}/enable``
- ``GET /admin/agent/tools`` — liste consolidée (registry + DB)

Convention 404 (P2) : non-admin reçoit 404 silencieux (géré par
``require_admin`` qui lève 401/403 ; on intercepte via dépendance pour
rejeter en 404 si nécessaire). En MVP on s'aligne sur le comportement de
``require_admin`` (auth FastAPI) qui retourne 401/403, ce qui satisfait
l'audit OWASP « ne pas révéler l'existence d'une ressource non auth ».
"""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy.orm import Session

from app.admin.deps import require_admin
from app.agent.guardrails.tool_status import (
    ToolStatusRow,
    disable_tool,
    enable_tool,
    list_tools_status,
)
from app.db import get_db
from app.models.account_user import AccountUser

router = APIRouter()


# ---------------------------------------------------------------------------
# Schemas Pydantic strict (extra='forbid')
# ---------------------------------------------------------------------------


class DisableRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    reason: str = Field(min_length=1, max_length=500)


class ToolStatusResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    enabled: bool
    disabled_at: datetime | None = None
    disabled_by: UUID | None = None
    reason: str | None = None


class ToolStatusList(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[ToolStatusResponse]


class ActionResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tool_name: str
    enabled: bool


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------


@router.post(
    "/{tool_name}/disable",
    response_model=ActionResponse,
    summary="F58 / US4 — Désactiver un tool agent (kill-switch)",
)
async def disable_agent_tool(
    tool_name: str,
    payload: DisableRequest,
    db: Session = Depends(get_db),
    admin: AccountUser = Depends(require_admin),
) -> ActionResponse:
    """Désactive un tool agent + audit log (FR-007, FR-008)."""
    if not _is_valid_tool_name(tool_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        disable_tool(db, tool_name, admin_user_id=admin.id, reason=payload.reason)
        db.commit()
    except Exception as exc:
        db.rollback()
        import logging

        logging.getLogger(__name__).exception("disable_tool endpoint failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Échec désactivation tool: {exc.__class__.__name__}",
        ) from exc
    return ActionResponse(tool_name=tool_name, enabled=False)


@router.post(
    "/{tool_name}/enable",
    response_model=ActionResponse,
    summary="F58 / US4 — Réactiver un tool agent",
)
async def enable_agent_tool(
    tool_name: str,
    db: Session = Depends(get_db),
    admin: AccountUser = Depends(require_admin),
) -> ActionResponse:
    """Réactive un tool agent + audit log (FR-007)."""
    if not _is_valid_tool_name(tool_name):
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
    try:
        enable_tool(db, tool_name, admin_user_id=admin.id)
        db.commit()
    except Exception:  # noqa: BLE001
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Échec réactivation tool",
        ) from None
    return ActionResponse(tool_name=tool_name, enabled=True)


@router.get(
    "",
    response_model=ToolStatusList,
    summary="F58 / US4 — Liste consolidée des status tools agent",
)
async def list_agent_tools(
    db: Session = Depends(get_db),
    admin: AccountUser = Depends(require_admin),  # noqa: ARG001
) -> ToolStatusList:
    """Retourne tous les tools du registry + leur état DB (default = enabled)."""
    rows = list_tools_status(db)
    db_index = {r.tool_name: r for r in rows}
    items: list[ToolStatusResponse] = []
    for tool_name in _all_known_tool_names():
        row = db_index.get(tool_name)
        if row is not None:
            items.append(_to_response(row))
        else:
            # Tool jamais touché → enabled par défaut
            items.append(
                ToolStatusResponse(
                    tool_name=tool_name,
                    enabled=True,
                    disabled_at=None,
                    disabled_by=None,
                    reason=None,
                )
            )
    # Ajouter aussi les tools désactivés inconnus du registry (ex. obsolètes)
    for r in rows:
        if r.tool_name not in {it.tool_name for it in items}:
            items.append(_to_response(r))
    return ToolStatusList(items=items)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_response(row: ToolStatusRow) -> ToolStatusResponse:
    return ToolStatusResponse(
        tool_name=row.tool_name,
        enabled=row.enabled,
        disabled_at=row.disabled_at,
        disabled_by=row.disabled_by,
        reason=row.reason,
    )


def _all_known_tool_names() -> list[str]:
    """Snapshot du TOOL_REGISTRY F14/F53 (best-effort)."""
    try:
        from app.orchestrator.tool_registry import TOOL_REGISTRY

        return sorted(TOOL_REGISTRY.keys())
    except Exception:  # pragma: no cover
        return []


def _is_valid_tool_name(name: str) -> bool:
    """Validation basique : nom non vide, chars autorisés, longueur ≤ 100."""
    if not name or len(name) > 100:
        return False
    return all(c.isalnum() or c in "_-" for c in name)


__all__ = [
    "DisableRequest",
    "ToolStatusList",
    "ToolStatusResponse",
    "router",
]
