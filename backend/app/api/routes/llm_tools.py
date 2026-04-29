"""F03 US2 — Routes HTTP internes pour les LLM tools.

Endpoint ``POST /internal/llm-tools/{name}`` consommé par Phase 3 (F14 LangGraph).
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.db import get_db
from app.schemas.source import (
    CiteSourceInput,
    CiteSourceOutput,
    FlagUnsourcedInput,
    FlagUnsourcedOutput,
    SearchSourceInput,
    SearchSourceOutput,
)
from app.services.llm_tools import (
    handle_cite_source,
    handle_flag_unsourced,
    handle_search_source,
)

router = APIRouter(prefix="/internal/llm-tools", tags=["llm-tools"])


@router.post("/cite_source", response_model=CiteSourceOutput)
def cite_source(
    payload: CiteSourceInput, db: Session = Depends(get_db)
) -> CiteSourceOutput:
    out = handle_cite_source(db, payload)
    if out.error == "not_verified":
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": "not_verified", "message": "Source non vérifiée."},
        )
    if out.error == "not_found":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "not_found", "message": "Source introuvable."},
        )
    return out


@router.post("/search_source", response_model=SearchSourceOutput)
def search_source(
    payload: SearchSourceInput, db: Session = Depends(get_db)
) -> SearchSourceOutput:
    return handle_search_source(db, payload)


@router.post("/flag_unsourced", response_model=FlagUnsourcedOutput)
def flag_unsourced(
    payload: FlagUnsourcedInput, db: Session = Depends(get_db)
) -> FlagUnsourcedOutput:
    return handle_flag_unsourced(db, payload)


@router.get("/specs", response_model=list[dict[str, Any]])
def get_specs() -> list[dict[str, Any]]:
    """Retourne les TOOL_SPECS function-calling (consommé par F14)."""
    from app.services.llm_tools import TOOL_SPECS
    return TOOL_SPECS
