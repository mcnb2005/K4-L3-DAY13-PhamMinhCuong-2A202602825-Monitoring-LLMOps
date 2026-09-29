from __future__ import annotations

import time
import uuid
import re

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from structlog.contextvars import bind_contextvars, clear_contextvars


class CorrelationIdMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        # BaseHTTPMiddleware can reuse a worker for many concurrent requests. Always
        # start from a clean context so metadata from one request cannot leak into
        # another one.
        clear_contextvars()

        supplied_id = request.headers.get("x-request-id", "").strip()
        if supplied_id and re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", supplied_id):
            correlation_id = supplied_id
        else:
            correlation_id = f"req-{uuid.uuid4().hex[:8]}"

        bind_contextvars(correlation_id=correlation_id)
        
        request.state.correlation_id = correlation_id
        
        start = time.perf_counter()
        response = await call_next(request)
        
        elapsed_ms = (time.perf_counter() - start) * 1000
        response.headers["x-request-id"] = correlation_id
        response.headers["x-response-time-ms"] = f"{elapsed_ms:.2f}"
        
        return response
