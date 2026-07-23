"""Convenience re-export — use `app.config.logging.get_logger` directly for new code."""
from app.config.logging import get_logger

__all__ = ["get_logger"]
