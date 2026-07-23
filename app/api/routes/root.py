"""GET / — root health message."""
from fastapi import APIRouter

from app.config.constants import APP_TITLE

router = APIRouter(tags=["root"])


@router.get("/")
def root():
    return {"message": f"{APP_TITLE} is running"}
