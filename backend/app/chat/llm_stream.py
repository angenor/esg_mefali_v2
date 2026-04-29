"""F13 — Générateur SSE pour la réponse assistant.

- Si ``LLM_API_KEY`` configuré ET ``LLM_STUB`` non actif → vrai client OpenRouter (streaming).
- Sinon : stub déterministe ``[F13 stub: LLM non configuré]`` + ``message_done``.

Le format des events suit ``contracts/sse-envelope.schema.json``.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)

STUB_TEXT = "[F13 stub: LLM non configuré]"


def _envelope(event_type: str, data: dict) -> str:
    return f"event: {event_type}\ndata: {json.dumps(data)}\n\n"


def _is_stub_mode() -> bool:
    if os.environ.get("LLM_STUB") == "1":
        return True
    api_key = os.environ.get("LLM_API_KEY") or ""
    if not api_key or api_key.startswith("sk-fake") or api_key == "test":
        return True
    return False


async def stream_assistant(
    *, user_content: str, message_id_factory
) -> AsyncIterator[tuple[str, str]]:
    """Yield ``(sse_text, accumulated_content)`` tuples.

    Le caller persiste le message final quand l'event ``message_done`` arrive.
    ``message_id_factory()`` doit retourner l'UUID du message assistant final.
    """
    accumulated_parts: list[str] = []

    if _is_stub_mode():
        # Stub : 3 deltas pour simuler le streaming, puis message_done.
        for chunk in (STUB_TEXT, "", ""):
            if chunk:
                accumulated_parts.append(chunk)
                yield _envelope("text_delta", {"delta": chunk}), "".join(accumulated_parts)
            await asyncio.sleep(0)
        msg_id = message_id_factory("".join(accumulated_parts))
        yield _envelope("message_done", {"message_id": str(msg_id)}), "".join(accumulated_parts)
        return

    # Vrai client OpenRouter (sync SDK -> wrap dans to_thread)
    try:
        from app.config import get_settings
        from app.llm_client import get_llm_client

        client = get_llm_client()
        settings = get_settings()

        def _call_sync():
            return client.chat.completions.create(
                model=settings.LLM_MODEL,
                messages=[{"role": "user", "content": user_content}],
                stream=True,
            )

        stream = await asyncio.to_thread(_call_sync)
        for chunk in stream:
            try:
                delta = chunk.choices[0].delta.content or ""
            except Exception:
                delta = ""
            if delta:
                accumulated_parts.append(delta)
                yield _envelope("text_delta", {"delta": delta}), "".join(accumulated_parts)
        msg_id = message_id_factory("".join(accumulated_parts))
        yield _envelope("message_done", {"message_id": str(msg_id)}), "".join(accumulated_parts)
    except Exception as exc:  # pragma: no cover
        logger.exception("LLM streaming failure: %s", exc)
        yield _envelope("error", {"code": "llm_error", "detail": str(exc)[:200]}), "".join(accumulated_parts)
