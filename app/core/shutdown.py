"""Runs once when the FastAPI app shuts down."""
from app.config.logging import get_logger
from app.database.session import engine

logger = get_logger(__name__)


def on_shutdown() -> None:
    engine.dispose()
    logger.info("Shut down.")
