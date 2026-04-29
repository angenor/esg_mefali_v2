"""F04 — Request-ID middleware (T028, T122, FR-018).

Generates or propagates ``X-Request-Id`` across the call stack so audit_log
rows can be joined to API requests end-to-end.
"""

from __future__ import annotations

from secrets import token_hex

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware

REQUEST_ID_HEADER = "x-request-id"


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Stores ``request_id`` on ``request.state`` and echoes it in the response."""

    async def dispatch(self, request: Request, call_next):
        rid = request.headers.get(REQUEST_ID_HEADER) or token_hex(12)
        request.state.request_id = rid
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = rid
        return response
