from app.database.base import Base
from app.database.session import engine
# Import models so they're registered on Base.metadata before create_all.
from app.database import patient_model, prediction_model, user_model  # noqa: F401


def test_tables_can_be_created():
    Base.metadata.create_all(bind=engine)
    assert True
