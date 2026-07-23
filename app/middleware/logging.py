"""Logs method, path, status code, and request ID for every request."""
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import Response

from app.config.logging import get_logger

logger = get_logger("app.request")


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        response = await call_next(request)
        request_id = getattr(request.state, "request_id", "-")
        logger.info(
            f'"{request.method} {request.url.path}" {response.status_code} request_id={request_id}'
        )
        return response
