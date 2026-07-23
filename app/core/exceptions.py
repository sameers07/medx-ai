"""App-specific exceptions and their FastAPI handlers."""
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config.logging import get_logger

logger = get_logger(__name__)


class AppError(Exception):
    """Base class for expected application errors — raise a subclass, not this directly."""

    status_code = 500

    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(AppError):
    status_code = 404


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return JSONResponse(status_code=exc.status_code, content={"detail": exc.message})

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception):
        logger.exception(f"Unhandled error on {request.method} {request.url.path}")
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})
