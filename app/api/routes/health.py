"""GET /health — liveness check."""
from fastapi import APIRouter

from app.config.constants import HEALTH_STATUS_OK

router = APIRouter(tags=["health"])


@router.get("/health")
def health():
    return {"status": HEALTH_STATUS_OK}
