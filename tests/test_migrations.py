"""Smoke test: Alembic's initial migration creates and tears down the full schema."""
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect

from app.config.settings import settings

REPO_ROOT = Path(__file__).parent.parent

EXPECTED_TABLES = {"users", "patients", "studies", "predictions"}


def _alembic_config() -> Config:
    cfg = Config(str(REPO_ROOT / "alembic.ini"))
    cfg.set_main_option("script_location", str(REPO_ROOT / "alembic"))
    return cfg


def test_upgrade_creates_all_tables(tmp_path, monkeypatch):
    db_path = tmp_path / "migration_test.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")

    command.upgrade(_alembic_config(), "head")

    tables = set(inspect(create_engine(settings.database_url)).get_table_names())
    assert EXPECTED_TABLES <= tables


def test_downgrade_drops_all_tables(tmp_path, monkeypatch):
    db_path = tmp_path / "migration_test.db"
    monkeypatch.setattr(settings, "database_url", f"sqlite:///{db_path}")

    cfg = _alembic_config()
    command.upgrade(cfg, "head")
    command.downgrade(cfg, "base")

    tables = set(inspect(create_engine(settings.database_url)).get_table_names())
    assert not (EXPECTED_TABLES & tables)
