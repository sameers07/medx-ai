"""
FastAPI application entrypoint. See docs/roadmap.md for what's wired up so far.
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.api.routes import health, history, predict, root, upload
from app.config.constants import APP_TITLE, APP_VERSION
from app.core.exceptions import register_exception_handlers
from app.core.shutdown import on_shutdown
from app.core.startup import on_startup
from app.middleware.logging import RequestLoggingMiddleware
from app.middleware.request_id import RequestIDMiddleware
from app.middleware.timing import TimingMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    on_startup()
    yield
    on_shutdown()


app = FastAPI(title=APP_TITLE, version=APP_VERSION, lifespan=lifespan)

# Starlette wraps outer-to-inner in reverse of add_middleware call order, so RequestID
# (added last) runs first and sets request.state.request_id before Logging reads it.
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(TimingMiddleware)
app.add_middleware(RequestIDMiddleware)

register_exception_handlers(app)

app.include_router(root.router)
app.include_router(health.router)
app.include_router(upload.router)
app.include_router(predict.router)
app.include_router(history.router)
