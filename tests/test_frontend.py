"""Smoke test: the Streamlit app renders without exceptions."""
from streamlit.testing.v1 import AppTest


def test_frontend_loads_without_exceptions():
    at = AppTest.from_file("frontend/app.py")
    at.run()
    assert not at.exception
