"""Back-compat facade. Prefer importing `Base` from app.database.base and
`engine`/`SessionLocal`/`get_db` from app.database.session directly.
"""
from app.database.base import Base
from app.database.session import SessionLocal, engine, get_db

__all__ = ["Base", "engine", "SessionLocal", "get_db"]
