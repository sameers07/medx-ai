"""Adds an X-Process-Time response header with the request's handling duration."""
import time

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config.constants import PROCESS_TIME_HEADER


class TimingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers[PROCESS_TIME_HEADER] = f"{duration_ms:.2f}ms"
        return response
