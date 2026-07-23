"""Declarative base — all ORM models inherit from this. Nothing else lives here."""
from sqlalchemy.orm import declarative_base

Base = declarative_base()
