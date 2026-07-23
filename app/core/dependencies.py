"""Central place for FastAPI `Depends()` targets shared across routes."""
from app.config.settings import Settings, settings
from app.database.session import get_db

__all__ = ["get_db", "get_settings"]


def get_settings() -> Settings:
    return settings
