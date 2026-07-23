"""Runs once when the FastAPI app starts."""
from app.config.logging import get_logger, setup_logging
from app.database.session import engine

logger = get_logger(__name__)


def on_startup() -> None:
    setup_logging()
    logger.info("Starting up...")
    # Fail fast if the DB is unreachable, rather than on the first request.
    with engine.connect():
        pass
    logger.info("Database connection OK.")
