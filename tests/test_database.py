from app.database.connection import Base, engine


def test_tables_can_be_created():
    Base.metadata.create_all(bind=engine)
    assert True
