"""F13 — Routes ``/me/chat/*`` et ``/me/events`` (REST + SSE).

Conforme à ``contracts/chat-api.openapi.yaml``.
"""

from __future__ import annotations

import json
import logging
from typing import Any
from uuid import UUID

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query, status
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from app.auth.dependencies import get_current_pme
from app.chat import event_bus, service
from app.chat import repository as repo
from app.chat.embedding_task import compute_and_store_embedding
from app.chat.llm_stream import stream_assistant
from app.chat.schemas import (
    ChatMessageListOut,
    ChatThreadCreateIn,
    ChatThreadListOut,
    ChatThreadOut,
    PostMessageBody,
)
from app.chat.service import ThreadArchivedError, ThreadNotFoundError
from app.config import get_settings
from app.db import get_db
from app.models.account_user import AccountUser

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/me/chat", tags=["chat"])


@router.get("/threads", response_model=ChatThreadListOut)
def list_threads(
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    rows = repo.list_threads(db, account_id=user.account_id, user_id=user.id, limit=200)
    return {"threads": rows}


@router.post("/threads", response_model=ChatThreadOut, status_code=status.HTTP_201_CREATED)
def create_thread(
    body: ChatThreadCreateIn | None = None,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    title = body.title if body else None
    row = service.create_thread(
        db, account_id=user.account_id, user_id=user.id, title=title
    )
    db.commit()
    return row


@router.delete("/threads/{thread_id}", status_code=status.HTTP_204_NO_CONTENT)
def archive_thread(
    thread_id: UUID,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> None:
    try:
        service.archive_thread(
            db, thread_id=thread_id, account_id=user.account_id, user_id=user.id
        )
    except ThreadNotFoundError as exc:
        raise HTTPException(status_code=404, detail="thread_not_found") from exc
    db.commit()
    return None


@router.get("/threads/{thread_id}/messages", response_model=ChatMessageListOut)
def list_messages(
    thread_id: UUID,
    after_id: UUID | None = Query(default=None),
    limit: int = Query(default=50, ge=1, le=200),
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> Any:
    thread = repo.get_thread_by_id(db, thread_id=thread_id, account_id=user.account_id)
    if not thread:
        raise HTTPException(status_code=404, detail="thread_not_found")
    rows = repo.list_messages(
        db,
        thread_id=thread_id,
        account_id=user.account_id,
        after_id=after_id,
        limit=limit,
    )
    return {"messages": rows}


@router.post("/threads/{thread_id}/messages")
def post_message(
    thread_id: UUID,
    body: PostMessageBody,
    background_tasks: BackgroundTasks,
    user: AccountUser = Depends(get_current_pme),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """Persiste le message user, retourne le stream SSE assistant.

    Le message assistant final est inséré quand le stream émet ``message_done``.
    """
    try:
        service.persist_user_turn(
            db,
            thread_id=thread_id,
            account_id=user.account_id,
            user_id=user.id,
            content=body.content,
            payload_json=body.payload_json,
            context_json=body.context_json,
        )
    except ThreadNotFoundError as exc:
        raise HTTPException(status_code=404, detail="thread_not_found") from exc
    except ThreadArchivedError as exc:
        raise HTTPException(status_code=409, detail="thread_archived") from exc

    db.commit()

    user_content = body.content
    account_id = user.account_id
    user_id = user.id

    # Capture du contenu final pour persister à message_done
    final_id_holder: dict[str, UUID] = {}

    def _persist_assistant(content: str) -> UUID:
        from app.db import SessionLocal

        db2 = SessionLocal()
        try:
            from sqlalchemy import text as _text
            db2.execute(_text(f"SET LOCAL app.current_account_id = '{account_id}'"))
            db2.execute(_text(f"SET LOCAL app.current_user_id = '{user_id}'"))
            mid = service.persist_assistant_turn(
                db2,
                thread_id=thread_id,
                account_id=account_id,
                user_id=user_id,
                content=content,
            )
            db2.commit()
            final_id_holder["id"] = mid
            return mid
        finally:
            db2.close()

    settings = get_settings()
    use_agent = settings.LLM_AGENT_MODE == "langgraph"

    if use_agent:
        # F53 — Agent LangGraph
        from app.agent.runner import (
            ThreadAccessDenied,
            make_thread_id,
            run_agent,
        )

        composite_thread_id = make_thread_id(account_id, conv_id=thread_id)
        ctx_payload = body.context_json or {"page_route": "/chat"}

        async def gen_agent():
            try:
                async for sse_line in run_agent(
                    account_id=account_id,
                    user_id=user_id,
                    thread_id=composite_thread_id,
                    user_message=user_content,
                    context_json=ctx_payload,
                ):
                    yield sse_line
            except ThreadAccessDenied:
                err = {"code": "not_found", "detail": "thread_not_found"}
                yield f"event: error\ndata: {json.dumps(err)}\n\n"
            except Exception as exc:  # noqa: BLE001
                logger.exception("agent post_message stream error: %s", exc)
                err = {"code": "stream_error", "detail": str(exc)[:200]}
                yield f"event: error\ndata: {json.dumps(err)}\n\n"

        return StreamingResponse(gen_agent(), media_type="text/event-stream")

    # Mode raw — proxy LLM brut (F13)
    async def gen():
        last_content = ""
        try:
            async for sse_text, accumulated in stream_assistant(
                user_content=user_content, message_id_factory=_persist_assistant
            ):
                last_content = accumulated
                yield sse_text
        except Exception as exc:  # pragma: no cover
            logger.exception("post_message stream error: %s", exc)
            err = {"code": "stream_error", "detail": str(exc)[:200]}
            yield f"event: error\ndata: {json.dumps(err)}\n\n"
        finally:
            mid = final_id_holder.get("id")
            if mid is not None and last_content:
                background_tasks.add_task(
                    compute_and_store_embedding, mid, last_content
                )

    return StreamingResponse(gen(), media_type="text/event-stream")


# --- /me/events ---
events_router = APIRouter(tags=["events"])


@events_router.get("/me/events")
async def me_events(
    user: AccountUser = Depends(get_current_pme),
) -> StreamingResponse:
    account_id = str(user.account_id)

    async def gen():
        async for msg in event_bus.subscribe(account_id):
            if msg.startswith(":"):
                yield msg
            else:
                # if msg is JSON we already serialized in publish
                try:
                    payload = json.loads(msg)
                    event_type = (
                        payload.get("type", "entity_updated")
                        if isinstance(payload, dict)
                        else "entity_updated"
                    )
                    data = payload.get("data", payload) if isinstance(payload, dict) else payload
                    yield f"event: {event_type}\ndata: {json.dumps(data)}\n\n"
                except Exception:
                    yield f"data: {msg}\n\n"

    return StreamingResponse(gen(), media_type="text/event-stream")
